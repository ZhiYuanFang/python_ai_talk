"""
类型关键字向量库（遗留）

业务说明：
独立 Collection feeding_type_cues，document 为短关键字。
主路径已改 OP 整段飞轮（feeding_op_cues），本库热路径已停用；
仅保留 admin / 迁移读取。新写入请用 op_cue_store。
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
from app.feeding.services.intent_cache_store import (
    INTENT_CACHE_QUALITY_DEFAULT,
    _is_confirm_only,
)

logger = logging.getLogger(__name__)

COLLECTION_NAME = "feeding_type_cues"
# TYPE 热路径严于 EVENT：抬高阈值减轻「睡了多久了」误命中 predict 短线索
TYPE_CUE_THRESHOLD = 0.9


def _as_type_cue_payload(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    规范类型载荷；拒绝整包 events。

    Returns:
        {target_type, op, history_mode, predict_channel, time_answer} 或 None
    """
    if not isinstance(payload, dict):
        return None
    if isinstance(payload.get("events"), list) and payload.get("events"):
        return None
    tt = str(payload.get("target_type") or "").strip().lower()
    op = str(payload.get("op") or "").strip().lower()
    hm = str(payload.get("history_mode") or "").strip().lower()
    pc = str(payload.get("predict_channel") or "").strip().lower()
    ta = str(payload.get("time_answer") or "").strip().lower()
    allowed = {"feeding", "history", "predict", "conversation", "exit"}
    if tt not in allowed:
        return None
    if tt == "history":
        op = "read"
        if hm not in ("point", "daily"):
            hm = "point"
        pc, ta = "", ""
    elif tt == "predict":
        # 预测：op/history_mode 清空；两维必须合法
        op = ""
        hm = ""
        if pc not in ("active", "next") or ta not in ("clock", "remain"):
            return None
    elif tt in ("conversation", "exit"):
        op = ""
        hm = ""
        pc, ta = "", ""
    elif not op:
        op = "create"
        hm = ""
        pc, ta = "", ""
    else:
        hm = hm if hm in ("point", "daily") else ""
        pc, ta = "", ""
    return {
        "target_type": tt,
        "op": op,
        "history_mode": hm,
        "predict_channel": pc,
        "time_answer": ta,
    }


class TypeCueStore:
    """类型关键字向量库。"""

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
                metadata={"description": "喂养类型关键字飞轮"},
            )
            self._initialized = True
            logger.info("类型关键字向量库初始化完成")

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
        """检索最相似类型关键字。"""
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
                "类型关键字检索: query=%s, document=%s, score=%s, target=%s",
                q[:80],
                str(top.get("document") or "")[:80],
                top.get("score"),
                (top.get("payload") or {}).get("target_type"),
            )
        return formatted

    def search_type_cue(self, query: str, n_results: int = 1) -> List[Dict[str, Any]]:
        """供 TYPE 维调用；调用方用 TYPE_CUE_THRESHOLD 过滤。"""
        return self.search(query, n_results=n_results)

    def add(self, document: str, payload: Dict[str, Any]) -> Optional[str]:
        """写入或更新一条类型关键字（运行时覆盖同 document）。"""
        self._ensure_initialized()
        doc = (document or "").strip()
        if not doc or _is_confirm_only(doc):
            logger.info("跳过类型关键字写入：空句或确认词")
            return None
        clean = _as_type_cue_payload(payload)
        if not clean:
            logger.info("跳过类型关键字写入：非法载荷 doc=%s", doc[:40])
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
                "更新类型关键字: id=%s, doc=%s, target=%s",
                existing_id,
                doc[:40],
                clean.get("target_type"),
            )
            return existing_id
        vector_id = f"typecue_{uuid.uuid4().hex}"
        self._collection.add(
            ids=[vector_id],
            embeddings=[embedding],
            documents=[doc],
            metadatas=[meta],
        )
        logger.info(
            "写入类型关键字: id=%s, doc=%s, target=%s",
            vector_id,
            doc[:40],
            clean.get("target_type"),
        )
        return vector_id

    def add_type_keywords(
        self,
        keywords: List[str],
        *,
        target_type: str,
        op: str = "",
        history_mode: str = "",
        predict_channel: str = "",
        time_answer: str = "",
    ) -> int:
        """
        按关键字列表写入同一类型 payload。

        Returns:
            成功写入条数
        """
        payload = {
            "target_type": target_type,
            "op": op,
            "history_mode": history_mode,
            "predict_channel": predict_channel,
            "time_answer": time_answer,
        }
        n = 0
        for kw in keywords or []:
            doc = (kw or "").strip()
            if not doc:
                continue
            if self.add(doc, payload):
                n += 1
        return n

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
            logger.info("已删除类型关键字: id=%s", vid)
            return True
        except Exception as exc:
            logger.error("类型关键字删除失败: %s", exc, exc_info=True)
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
            if not _as_type_cue_payload(payload):
                failed.append({"index": i, "reason": "非法类型载荷"})
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
                logger.error("type bulk 第 %s 条失败: %s", i, exc, exc_info=True)
                failed.append({"index": i, "reason": str(exc)})
        return {
            "ok": added,
            "added": added,
            "skipped": skipped,
            "failed": failed,
            "ids": ids,
        }


type_cue_store = TypeCueStore()
