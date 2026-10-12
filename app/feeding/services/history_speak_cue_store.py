"""
查史播报策略整段飞轮

业务说明：
独立 Collection feeding_history_speak_cues，document MUST 为段整句原文（硬切），
payload 含 point_pick / open_speak。
短关键词主命中/主回写已停用；过短 document 热路径拒绝。
管理端 bulk 同 document 跳过。
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from app.config.settings import settings
from app.feeding.services.intent_cache_store import (
    INTENT_CACHE_QUALITY_DEFAULT,
    _is_confirm_only,
)

logger = logging.getLogger(__name__)

COLLECTION_NAME = "feeding_history_speak_cues"
# 与 OP 整段同严
HISTORY_SPEAK_CUE_THRESHOLD = 0.9
# 短于该长度视为旧短词残留，热路径拒绝
MIN_FULL_UTTERANCE_LEN = 4

POINT_PICK_VALUES = frozenset({"latest", "prefer_completed"})
OPEN_SPEAK_VALUES = frozenset({"elapsed", "in_progress"})


def as_history_speak_payload(
    payload: Dict[str, Any],
) -> Optional[Dict[str, str]]:
    """
    规范查史播报载荷。

    Returns:
        {point_pick, open_speak} 或 None
    """
    if not isinstance(payload, dict):
        return None
    pp = str(payload.get("point_pick") or "").strip().lower()
    os_ = str(payload.get("open_speak") or "").strip().lower()
    if pp not in POINT_PICK_VALUES or os_ not in OPEN_SPEAK_VALUES:
        return None
    return {"point_pick": pp, "open_speak": os_}


class HistorySpeakCueStore:
    """查史播报策略关键字向量库。"""

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
                metadata={"description": "查史播报策略整段飞轮"},
            )
            self._initialized = True
            logger.info("查史播报策略整段飞轮初始化完成")

    def _embed(self, texts: List[str]) -> List[List[float]]:
        return self._embedding_model.encode(texts).tolist()

    @staticmethod
    def _document_key(document: str) -> str:
        return (document or "").strip()

    def _find_id_by_document(self, doc: str) -> Optional[str]:
        key = self._document_key(doc)
        if not key:
            return None
        data = self._collection.get(include=["documents"])
        docs = data.get("documents") or []
        ids = data.get("ids") or []
        for i, existing in enumerate(docs):
            if self._document_key(existing or "") == key:
                return ids[i]
        return None

    def search(self, query: str, n_results: int = 1) -> List[Dict[str, Any]]:
        """检索最相似策略关键字。"""
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
        if formatted:
            top = formatted[0]
            logger.info(
                "查史播报关键字检索: query=%s, document=%s, score=%s, pick=%s",
                q[:80],
                str(top.get("document") or "")[:80],
                top.get("score"),
                (top.get("payload") or {}).get("point_pick"),
            )
        return formatted

    def search_policy(
        self, query: str
    ) -> Optional[Tuple[str, str]]:
        """
        热路径：整段命中且分数达标、两维合法则返回策略。

        硬切：过短 document 拒绝；非全文相等须更高分。
        """
        hits = self.search(query, n_results=1)
        if not hits:
            return None
        top = hits[0]
        score = float(top.get("score") or 0)
        if score < HISTORY_SPEAK_CUE_THRESHOLD:
            return None
        doc = self._document_key(str(top.get("document") or ""))
        q = self._document_key(query)
        if len(doc) < MIN_FULL_UTTERANCE_LEN:
            logger.info("查史播报拒绝短词 document: %s", doc)
            return None
        if doc != q and score < 0.95:
            return None
        clean = as_history_speak_payload(top.get("payload") or {})
        if not clean:
            return None
        return clean["point_pick"], clean["open_speak"]

    def add(self, document: str, payload: Dict[str, Any]) -> Optional[str]:
        """写入或更新一条整段策略。"""
        self._ensure_initialized()
        doc = (document or "").strip()
        if not doc or _is_confirm_only(doc):
            logger.info("跳过查史播报写入：空句或确认词")
            return None
        if len(doc) < MIN_FULL_UTTERANCE_LEN:
            logger.info("跳过查史播报写入：过短非整段 doc=%s", doc)
            return None
        clean = as_history_speak_payload(payload)
        if not clean:
            logger.info("跳过查史播报写入：非法载荷 doc=%s", doc[:40])
            return None
        embedding = self._embed([doc])[0]
        meta = {
            "payload": json.dumps(clean, ensure_ascii=False),
            "created_at": datetime.now().isoformat(),
            "quality_score": INTENT_CACHE_QUALITY_DEFAULT,
        }
        existing_id = self._find_id_by_document(doc)
        if existing_id:
            self._collection.update(
                ids=[existing_id],
                embeddings=[embedding],
                documents=[doc],
                metadatas=[meta],
            )
            logger.info(
                "更新查史播报关键字: id=%s, doc=%s, pick=%s",
                existing_id,
                doc[:40],
                clean.get("point_pick"),
            )
            return existing_id
        vector_id = f"hscue_{uuid.uuid4().hex}"
        self._collection.add(
            ids=[vector_id],
            embeddings=[embedding],
            documents=[doc],
            metadatas=[meta],
        )
        logger.info(
            "写入查史播报关键字: id=%s, doc=%s, pick=%s",
            vector_id,
            doc[:40],
            clean.get("point_pick"),
        )
        return vector_id

    def add_keywords(
        self,
        keywords: List[str],
        *,
        point_pick: str,
        open_speak: str,
    ) -> int:
        """
        遗留 API：硬切后不再按短关键词写入。

        仅当单条 keyword 自身已达整段长度时才写入（兼容误调）。
        """
        logger.info("add_keywords 已停用短词主策略，忽略短线索写入")
        payload = {"point_pick": point_pick, "open_speak": open_speak}
        n = 0
        for kw in keywords or []:
            doc = (kw or "").strip()
            if len(doc) < MIN_FULL_UTTERANCE_LEN:
                continue
            if self.add(doc, payload):
                n += 1
        return n

    def clear_short_documents(self, *, max_len: int = MIN_FULL_UTTERANCE_LEN) -> int:
        """硬切：删除过短旧短词条目。"""
        self._ensure_initialized()
        data = self._collection.get(include=["documents"])
        ids = data.get("ids") or []
        docs = data.get("documents") or []
        to_del = [
            ids[i]
            for i, d in enumerate(docs)
            if len(self._document_key(d or "")) < max_len
        ]
        if to_del:
            self._collection.delete(ids=to_del)
            logger.info("查史播报已清除短词条目: n=%s", len(to_del))
        return len(to_del)

    def list_entries(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """分页列出（created_at 新→旧）。"""
        self._ensure_initialized()
        data = self._collection.get(include=["documents", "metadatas"])
        ids = data.get("ids") or []
        docs = data.get("documents") or []
        metas = data.get("metadatas") or []
        total = len(ids)
        all_items: List[Dict[str, Any]] = []
        for i in range(total):
            meta = metas[i] or {}
            payload_raw = meta.get("payload") or "{}"
            try:
                payload = json.loads(payload_raw)
            except (TypeError, ValueError, json.JSONDecodeError):
                payload = {}
            try:
                quality = float(meta.get("quality_score", INTENT_CACHE_QUALITY_DEFAULT))
            except (TypeError, ValueError):
                quality = INTENT_CACHE_QUALITY_DEFAULT
            all_items.append(
                {
                    "id": ids[i],
                    "document": docs[i] if i < len(docs) else "",
                    "quality_score": quality,
                    "payload": payload,
                    "created_at": meta.get("created_at") or "",
                }
            )
        all_items.sort(key=lambda x: str(x.get("id") or ""))
        all_items.sort(
            key=lambda x: str(x.get("created_at") or ""),
            reverse=True,
        )
        start = max(0, int(offset))
        page_limit = max(1, min(int(limit), 500))
        return {
            "total": total,
            "offset": start,
            "limit": page_limit,
            "items": all_items[start : start + page_limit],
        }

    def delete_by_id(self, vector_id: str) -> bool:
        """按 id 删除。"""
        self._ensure_initialized()
        vid = (vector_id or "").strip()
        if not vid:
            return False
        try:
            existing = self._collection.get(ids=[vid], include=[])
            if not (existing.get("ids") or []):
                return False
            self._collection.delete(ids=[vid])
            logger.info("已删除查史播报关键字: id=%s", vid)
            return True
        except Exception as exc:
            logger.error("查史播报关键字删除失败: %s", exc, exc_info=True)
            return False

    def dedupe_exact_documents(self) -> Dict[str, Any]:
        """同 document 每组留一条。"""
        self._ensure_initialized()
        data = self._collection.get(include=["documents", "metadatas"])
        ids = data.get("ids") or []
        docs = data.get("documents") or []
        metas = data.get("metadatas") or []
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for i, vid in enumerate(ids):
            doc = docs[i] if i < len(docs) else ""
            key = self._document_key(doc)
            if not key:
                continue
            meta = metas[i] if i < len(metas) else None
            meta = meta or {}
            try:
                quality = float(meta.get("quality_score", INTENT_CACHE_QUALITY_DEFAULT))
            except (TypeError, ValueError):
                quality = INTENT_CACHE_QUALITY_DEFAULT
            groups.setdefault(key, []).append(
                {
                    "id": vid,
                    "document": doc,
                    "quality_score": quality,
                    "created_at": str(meta.get("created_at") or ""),
                }
            )
        kept = 0
        deleted: List[Dict[str, Any]] = []
        dup_groups = 0
        for key, members in groups.items():
            if len(members) <= 1:
                kept += len(members)
                continue
            dup_groups += 1
            members_sorted = sorted(
                members,
                key=lambda m: (
                    -float(m.get("quality_score") or 0),
                    str(m.get("created_at") or ""),
                    str(m.get("id") or ""),
                ),
            )
            kept += 1
            for loser in members_sorted[1:]:
                vid = str(loser.get("id") or "")
                if self.delete_by_id(vid):
                    deleted.append(
                        {
                            "id": vid,
                            "document": loser.get("document") or key,
                            "quality_score": loser.get("quality_score"),
                        }
                    )
        return {"kept": kept, "deleted": deleted, "groups": dup_groups}

    def bulk_upsert(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """管理端批量：同 document 跳过。"""
        self._ensure_initialized()
        added = 0
        ids: List[str] = []
        failed: List[Dict[str, Any]] = []
        skipped: List[Dict[str, Any]] = []
        seen: Dict[str, str] = {}
        for i, entry in enumerate(entries or []):
            if not isinstance(entry, dict):
                failed.append({"index": i, "reason": "条目不是对象"})
                continue
            doc = self._document_key(str(entry.get("document") or ""))
            payload = entry.get("payload")
            if not isinstance(payload, dict):
                payload = {}
            if not doc or _is_confirm_only(doc):
                failed.append({"index": i, "reason": "空句或确认词，未写入"})
                continue
            if not as_history_speak_payload(payload):
                failed.append({"index": i, "reason": "非法策略载荷"})
                continue
            try:
                existing_id = seen.get(doc) or self._find_id_by_document(doc)
                if existing_id:
                    skipped.append(
                        {
                            "index": i,
                            "document": doc,
                            "existing_id": existing_id,
                        }
                    )
                    seen[doc] = existing_id
                    continue
                vid = self.add(doc, payload)
                if not vid:
                    failed.append({"index": i, "reason": "写入失败"})
                    continue
                added += 1
                ids.append(vid)
                seen[doc] = vid
            except Exception as exc:
                logger.error("history-speak bulk 第 %s 条失败: %s", i, exc, exc_info=True)
                failed.append({"index": i, "reason": str(exc)})
        return {
            "ok": added,
            "added": added,
            "skipped": skipped,
            "failed": failed,
            "ids": ids,
        }


history_speak_cue_store = HistorySpeakCueStore()
