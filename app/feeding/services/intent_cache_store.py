"""
意图缓存飞轮存储

业务说明：
独立 Collection feeding_intents，document 为改写后的独立问答句，
metadata 为整份 CRUD 意图（op + events + 可选 remark_keyword）。
确认且至少一条落库成功后写入；改/删不得固化 history_id。
「嗯/是的」等续聊词不得当 document。
"""

from __future__ import annotations

import json
import logging
import os
import threading
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

# 高置信采用缓存（与事件向量高置信同量级，实现时再标定）
INTENT_CACHE_HIGH_THRESHOLD = 0.72


def _is_confirm_only(text: str) -> bool:
    """判断是否为不能单独成句的确认词。"""
    t = (text or "").strip().strip("。．.!！?？")
    return t.casefold() in {w.casefold() for w in _CONFIRM_ONLY}


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
                name="feeding_intents",
                metadata={"description": "喂养意图缓存飞轮"},
            )
            self._initialized = True
            logger.info("意图缓存向量库初始化完成")

    def _embed(self, texts: List[str]) -> List[List[float]]:
        return self._embedding_model.encode(texts).tolist()

    def search(self, query: str, n_results: int = 1) -> List[Dict[str, Any]]:
        """
        检索最相似的已缓存意图。

        Returns:
            含 score、document、payload 的列表
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
            formatted.append(
                {
                    "id": ids[i],
                    "score": round(score, 4),
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
        写入一条意图缓存。

        业务逻辑：
        确认词不写；payload 去掉 history_id 后再序列化。
        """
        self._ensure_initialized()
        doc = (document or "").strip()
        if not doc or _is_confirm_only(doc):
            logger.info("跳过意图缓存写入：空句或确认词")
            return None
        clean = _strip_history_ids(payload)
        vector_id = f"intent_{uuid.uuid4().hex}"
        embedding = self._embed([doc])[0]
        self._collection.add(
            ids=[vector_id],
            embeddings=[embedding],
            documents=[doc],
            metadatas=[
                {
                    "payload": json.dumps(clean, ensure_ascii=False),
                    "created_at": datetime.now().isoformat(),
                }
            ],
        )
        logger.info(f"写入意图缓存: id={vector_id}, doc={doc[:40]}...")
        return vector_id


def _strip_history_ids(payload: Dict[str, Any]) -> Dict[str, Any]:
    """去掉改/删不可复用的 history_id。"""
    out = dict(payload or {})
    out.pop("history_id", None)
    events = []
    for ev in out.get("events") or []:
        if not isinstance(ev, dict):
            continue
        item = dict(ev)
        item.pop("history_id", None)
        events.append(item)
    out["events"] = events
    return out


intent_cache_store = IntentCacheStore()
