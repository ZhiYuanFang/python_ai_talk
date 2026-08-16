"""
意图缓存飞轮存储

业务说明：
独立 Collection feeding_intents，document 为改写后的独立问答句，
顶层 metadata 含 quality_score 与 payload（op + events + 可选 remark_keyword）。
确认且至少一条落库/播报成功后写入；同一 document 更新而非新 uuid。
检索须相似度与质量分双门槛。短窗重复同一问扣分。
「嗯/是的」等续聊词不得当 document。
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from app.config.settings import settings

logger = logging.getLogger(__name__)

# 续聊确认词：禁止作为缓存 document
_CONFIRM_ONLY = {
    "嗯",
    "嗯嗯",
    "是的",
    "是",
    "对",
    "好",
    "好的",
    "确认",
    "1",
    "ok",
    "yes",
}

# 高置信采用缓存
INTENT_CACHE_HIGH_THRESHOLD = 0.72
# 质量分下限；缺省按 0.8
INTENT_CACHE_QUALITY_MIN = 0.7
INTENT_CACHE_QUALITY_DEFAULT = 0.8
INTENT_CACHE_QUALITY_PENALTY = 0.2
INTENT_CACHE_CLEANUP_THRESHOLD = 0.3
# 同一设备短窗内重复同一问视为否决刚免确认的那次
INTENT_CACHE_REPEAT_WINDOW_S = 180

_PUNCT_RE = re.compile(r"[。．.!！?？、，,；;：:\s]+")

COLLECTION_NAME = "feeding_intents"


def _is_confirm_only(text: str) -> bool:
    """判断是否为不能单独成句的确认词。"""
    t = (text or "").strip().strip("。．.!！?？")
    return t.casefold() in {w.casefold() for w in _CONFIRM_ONLY}


def normalize_intent_text(text: str) -> str:
    """短窗比较用：去空白与句末标点。"""
    t = (text or "").strip()
    t = _PUNCT_RE.sub("", t)
    return t.casefold()


class LastCacheTurnStore:
    """
    按设备记住最近一次意图缓存免确认执行。

    业务说明：
    冷启动常无 conversation_id，所以用 device_no。
    窗内同一问再来 → 扣分并当未命中。
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # device_no -> {text, vector_id, ts}
        self._turns: Dict[str, Dict[str, Any]] = {}

    def remember(self, device_no: str, text: str, vector_id: str) -> None:
        """缓存免确认执行成功后记下本轮。"""
        key = (device_no or "").strip()
        vid = (vector_id or "").strip()
        norm = normalize_intent_text(text)
        if not key or not vid or not norm:
            return
        with self._lock:
            self._turns[key] = {
                "text": norm,
                "vector_id": vid,
                "ts": time.time(),
            }

    def repeat_vector_id(self, device_no: str, text: str) -> Optional[str]:
        """
        若短窗内同一问刚免确认执行过，返回那条向量 id。
        """
        key = (device_no or "").strip()
        norm = normalize_intent_text(text)
        if not key or not norm:
            return None
        now = time.time()
        with self._lock:
            item = self._turns.get(key)
            if not item:
                return None
            if now - float(item.get("ts") or 0) > INTENT_CACHE_REPEAT_WINDOW_S:
                self._turns.pop(key, None)
                return None
            if item.get("text") != norm:
                return None
            return str(item.get("vector_id") or "") or None


last_cache_turn_store = LastCacheTurnStore()


class IntentCacheStore:
    """
    意图缓存向量库。

    业务说明：
    与知识库 Collection 物理隔离；事件名向量 feeding_events 已拆除。
    """

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = False
        self._init_lock = threading.Lock()

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            os.makedirs(settings.chroma_persist_dir, exist_ok=True)
            self._embedding_model = SentenceTransformer(
                settings.embedding_model,
                cache_folder=os.path.join("data", "models"),
                local_files_only=True,
            )
            self._chroma_client = chromadb.PersistentClient(
                path=settings.chroma_persist_dir,
                settings=Settings(anonymized_telemetry=False, allow_reset=False),
            )
            self._collection = self._chroma_client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"description": "喂养意图缓存飞轮"},
            )
            self._initialized = True
            logger.info("意图缓存向量库初始化完成")

    def _embed(self, texts: List[str]) -> List[List[float]]:
        return self._embedding_model.encode(texts).tolist()

    def _find_id_by_document(self, doc: str) -> Optional[str]:
        """按 document 原文找已有 id，避免 uuid 分身绕开扣分。"""
        data = self._collection.get(include=["documents"])
        docs = data.get("documents") or []
        ids = data.get("ids") or []
        for i, existing in enumerate(docs):
            if existing == doc:
                return ids[i]
        return None

    def search(self, query: str, n_results: int = 1) -> List[Dict[str, Any]]:
        """
        检索最相似的已缓存意图。

        Returns:
            含 score、quality_score、document、payload 的列表
        """
        self._ensure_initialized()
        q = (query or "").strip()
        if not q or _is_confirm_only(q):
            return []
        embedding = self._embed([q])[0]
        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=max(1, n_results),
            include=["documents", "metadatas", "distances"],
        )
        formatted: List[Dict[str, Any]] = []
        ids = (results.get("ids") or [[]])[0]
        for i in range(len(ids)):
            distance = results["distances"][0][i]
            score = 1 / (1 + distance)
            meta = results["metadatas"][0][i] or {}
            payload_raw = meta.get("payload") or "{}"
            try:
                payload = json.loads(payload_raw)
            except json.JSONDecodeError:
                payload = {}
            # 旧条没有质量分时按默认 0.8
            try:
                quality = float(meta.get("quality_score", INTENT_CACHE_QUALITY_DEFAULT))
            except (TypeError, ValueError):
                quality = INTENT_CACHE_QUALITY_DEFAULT
            formatted.append(
                {
                    "id": ids[i],
                    "score": round(score, 4),
                    "quality_score": quality,
                    "document": (results.get("documents") or [[]])[0][i],
                    "payload": payload,
                }
            )
        return formatted

    def add(
        self,
        document: str,
        payload: Dict[str, Any],
    ) -> Optional[str]:
        """
        写入或更新一条意图缓存。

        业务逻辑：
        确认词不写；payload 去掉 history_id；同一 document 更新并重置质量分为 0.8。
        """
        self._ensure_initialized()
        doc = (document or "").strip()
        if not doc or _is_confirm_only(doc):
            logger.info("跳过意图缓存写入：空句或确认词")
            return None
        clean = _strip_history_ids(payload)
        embedding = self._embed([doc])[0]
        meta = {
            "payload": json.dumps(clean, ensure_ascii=False),
            "created_at": datetime.now().isoformat(),
            "quality_score": INTENT_CACHE_QUALITY_DEFAULT,
        }
        existing_id = self._find_id_by_document(doc)
        if existing_id:
            # 用户再次确认同一句：覆盖载荷，质量分回到默认（不是给旧条偷偷 +0.1）
            self._collection.update(
                ids=[existing_id],
                embeddings=[embedding],
                documents=[doc],
                metadatas=[meta],
            )
            logger.info(f"更新意图缓存: id={existing_id}, doc={doc[:40]}...")
            return existing_id
        vector_id = f"intent_{uuid.uuid4().hex}"
        self._collection.add(
            ids=[vector_id],
            embeddings=[embedding],
            documents=[doc],
            metadatas=[meta],
        )
        logger.info(f"写入意图缓存: id={vector_id}, doc={doc[:40]}...")
        return vector_id

    def penalize(
        self,
        vector_id: str,
        delta: float = INTENT_CACHE_QUALITY_PENALTY,
    ) -> None:
        """短窗重复同一问：对该条质量分扣 delta，下限 0。"""
        self._ensure_initialized()
        vid = (vector_id or "").strip()
        if not vid:
            return
        try:
            existing = self._collection.get(ids=[vid], include=["metadatas"])
            metas = existing.get("metadatas") or []
            if not metas or not metas[0]:
                logger.warning(f"意图缓存扣分跳过：找不到 id={vid}")
                return
            meta = dict(metas[0])
            try:
                current = float(meta.get("quality_score", INTENT_CACHE_QUALITY_DEFAULT))
            except (TypeError, ValueError):
                current = INTENT_CACHE_QUALITY_DEFAULT
            new_score = max(0.0, current - float(delta))
            meta["quality_score"] = new_score
            meta["updated_at"] = datetime.now().isoformat()
            self._collection.update(ids=[vid], metadatas=[meta])
            logger.info(
                "意图缓存扣分: id=%s, quality %.4f -> %.4f",
                vid,
                current,
                new_score,
            )
        except Exception as exc:
            logger.error(f"意图缓存扣分失败: {exc}", exc_info=True)

    def cleanup_low_quality(
        self, threshold: float = INTENT_CACHE_CLEANUP_THRESHOLD
    ) -> int:
        """
        删除质量分低于阈值的意图缓存。

        MUST NOT 触碰 mother_baby_knowledge。
        """
        self._ensure_initialized()
        data = self._collection.get(include=["metadatas"])
        to_delete: List[str] = []
        for i, meta in enumerate(data.get("metadatas") or []):
            try:
                quality = float((meta or {}).get("quality_score", INTENT_CACHE_QUALITY_DEFAULT))
            except (TypeError, ValueError):
                quality = INTENT_CACHE_QUALITY_DEFAULT
            if quality < threshold:
                to_delete.append(data["ids"][i])
        if to_delete:
            self._collection.delete(ids=to_delete)
            logger.info(
                "意图缓存低分清理: 删除 %s 条, threshold=%s",
                len(to_delete),
                threshold,
            )
        return len(to_delete)

    def reset_collection(self) -> None:
        """
        启动一次性清空 feeding_intents。

        仅删除本 Collection，不得动知识库。
        """
        self._ensure_initialized()
        try:
            self._chroma_client.delete_collection(COLLECTION_NAME)
        except Exception as exc:
            logger.warning(f"删除 feeding_intents 集合时忽略: {exc}")
        self._collection = self._chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "喂养意图缓存飞轮"},
        )
        logger.warning("已按开关清空意图缓存 Collection feeding_intents")


def _strip_history_ids(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    去掉改/删不可复用的 history_id；并清空 event_id 仅保留名/动作（可移植飞轮）。

    命中后再用当前租户事件字典把名称解析回 id。
    """
    out = dict(payload or {})
    out.pop("history_id", None)
    events = []
    for ev in out.get("events") or []:
        if not isinstance(ev, dict):
            continue
        item = dict(ev)
        item.pop("history_id", None)
        # 可移植：不缓存租户 event_id
        item["event_id"] = ""
        events.append(item)
    out["events"] = events
    return out


intent_cache_store = IntentCacheStore()
