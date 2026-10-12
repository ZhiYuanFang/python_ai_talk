"""
时间相对配方整段飞轮

业务说明：
Collection feeding_time_cues，document 为段整句，
payload 仅为相对配方（validate_time_formula），禁止绝对 Unix 主缓存。
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
from app.feeding.services.time_formula import validate_time_formula

logger = logging.getLogger(__name__)

COLLECTION_NAME = "feeding_time_cues"
TIME_CUE_THRESHOLD = 0.9


class TimeCueStore:
    """时间相对配方整段向量库。"""

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
                metadata={"description": "时间相对配方整段飞轮"},
            )
            self._initialized = True
            logger.info("时间飞轮初始化完成")

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
            try:
                payload = json.loads(meta.get("payload") or "{}")
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

    def search_formula(self, query: str) -> Optional[Dict[str, Any]]:
        """热路径：命中达标返回规范化相对配方。"""
        hits = self.search(query, n_results=1)
        if not hits:
            return None
        top = hits[0]
        score = float(top.get("score") or 0)
        if score < TIME_CUE_THRESHOLD:
            return None
        doc = self._document_key(str(top.get("document") or ""))
        q = self._document_key(query)
        if doc != q and score < 0.95:
            return None
        clean = validate_time_formula(top.get("payload") or {})
        if not clean:
            return None
        logger.info(
            "时间飞轮命中: kind=%s score=%s",
            clean.get("kind"),
            score,
        )
        return clean

    def add(self, document: str, formula: Dict[str, Any]) -> Optional[str]:
        """仅合法相对配方可写；拒绝绝对 Unix 主载荷。"""
        self._ensure_initialized()
        doc = self._document_key(document)
        clean = validate_time_formula(formula)
        if not doc or _is_confirm_only(doc) or not clean:
            return None
        # 拒收夹带 Unix 主字段的「伪配方」
        if isinstance(formula, dict) and (
            formula.get("start_time") or formula.get("end_time")
        ):
            # 允许外层多字段，但写入只保留 clean
            pass
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
            return existing_id
        vector_id = f"tmcue_{uuid.uuid4().hex}"
        self._collection.add(
            ids=[vector_id],
            embeddings=[embedding],
            documents=[doc],
            metadatas=[meta],
        )
        logger.info("写入时间飞轮: id=%s kind=%s", vector_id, clean.get("kind"))
        return vector_id

    def list_entries(
        self, *, offset: int = 0, limit: int = 100
    ) -> Dict[str, Any]:
        self._ensure_initialized()
        data = self._collection.get(include=["documents", "metadatas"])
        ids = data.get("ids") or []
        docs = data.get("documents") or []
        metas = data.get("metadatas") or []
        items: List[Dict[str, Any]] = []
        for i, vid in enumerate(ids):
            meta = metas[i] or {}
            try:
                payload = json.loads(meta.get("payload") or "{}")
            except (TypeError, ValueError, json.JSONDecodeError):
                payload = {}
            items.append(
                {
                    "id": vid,
                    "document": docs[i] if i < len(docs) else "",
                    "payload": payload,
                    "created_at": meta.get("created_at") or "",
                }
            )
        items.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
        start = max(0, int(offset))
        lim = max(1, min(500, int(limit)))
        return {
            "total": len(items),
            "offset": start,
            "limit": lim,
            "items": items[start : start + lim],
        }

    def delete_by_id(self, vector_id: str) -> bool:
        self._ensure_initialized()
        vid = (vector_id or "").strip()
        if not vid:
            return False
        try:
            existing = self._collection.get(ids=[vid], include=[])
            if not (existing.get("ids") or []):
                return False
            self._collection.delete(ids=[vid])
            return True
        except Exception as exc:
            logger.error("时间飞轮删除失败: %s", exc, exc_info=True)
            return False

    def bulk_upsert(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        self._ensure_initialized()
        added = 0
        ids: List[str] = []
        failed: List[Dict[str, Any]] = []
        skipped: List[Dict[str, Any]] = []
        for i, entry in enumerate(entries or []):
            if not isinstance(entry, dict):
                failed.append({"index": i, "reason": "非对象"})
                continue
            doc = self._document_key(str(entry.get("document") or ""))
            payload = (
                entry.get("payload") if isinstance(entry.get("payload"), dict) else {}
            )
            if not doc:
                failed.append({"index": i, "reason": "空 document"})
                continue
            # 拒绝仅 Unix、无合法配方
            if not validate_time_formula(payload):
                failed.append(
                    {"index": i, "reason": "缺少合法相对配方或仅含绝对 Unix"}
                )
                continue
            if self._find_id_by_document(doc):
                skipped.append({"index": i, "document": doc})
                continue
            vid = self.add(doc, payload)
            if not vid:
                failed.append({"index": i, "reason": "写入失败"})
                continue
            added += 1
            ids.append(vid)
        return {
            "ok": added,
            "added": added,
            "skipped": skipped,
            "failed": failed,
            "ids": ids,
        }


time_cue_store = TimeCueStore()
