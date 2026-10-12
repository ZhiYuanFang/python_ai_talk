"""
OP 轨整段飞轮

业务说明：
独立 Collection feeding_op_cues，document 为段整句原文，
payload 仅含 op_rail（create|read|update|delete|exit|other）。
热路径命中跳过 OP 小 LLM；禁止短关键词主策略；与事件/类型旧库隔离。
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
from app.shared.constants import TARGET_TYPE_RAILS

logger = logging.getLogger(__name__)

COLLECTION_NAME = "feeding_op_cues"
# 整段命中从严，宁可不中
OP_CUE_THRESHOLD = 0.9


def as_op_rail_payload(payload: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """规范 OP 载荷；仅允许六轨。"""
    if not isinstance(payload, dict):
        return None
    rail = str(
        payload.get("op_rail") or payload.get("target_type") or ""
    ).strip().lower()
    if rail not in TARGET_TYPE_RAILS:
        return None
    return {"op_rail": rail}


class OpCueStore:
    """OP 轨整段向量库。"""

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
                metadata={"description": "OP 轨整段飞轮"},
            )
            self._initialized = True
            logger.info("OP 轨飞轮初始化完成")

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
        """检索最相似整段。"""
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

    def search_op_rail(self, query: str) -> Optional[str]:
        """热路径：命中且达标则返回 op_rail。"""
        hits = self.search(query, n_results=1)
        if not hits:
            return None
        top = hits[0]
        if float(top.get("score") or 0) < OP_CUE_THRESHOLD:
            return None
        # 整段策略：document 须与查询足够接近（同文或高分）
        doc = self._document_key(str(top.get("document") or ""))
        q = self._document_key(query)
        if doc != q and float(top.get("score") or 0) < 0.95:
            # 非全文相等时要求更高分，降低短词误命中
            return None
        clean = as_op_rail_payload(top.get("payload") or {})
        if not clean:
            return None
        logger.info(
            "OP 飞轮命中: rail=%s score=%s doc=%s",
            clean["op_rail"],
            top.get("score"),
            doc[:40],
        )
        return clean["op_rail"]

    def add(self, document: str, op_rail: str) -> Optional[str]:
        """写入/更新整段 → op_rail。"""
        self._ensure_initialized()
        doc = self._document_key(document)
        if not doc or _is_confirm_only(doc):
            return None
        clean = as_op_rail_payload({"op_rail": op_rail})
        if not clean:
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
            return existing_id
        vector_id = f"opcue_{uuid.uuid4().hex}"
        self._collection.add(
            ids=[vector_id],
            embeddings=[embedding],
            documents=[doc],
            metadatas=[meta],
        )
        logger.info("写入 OP 飞轮: id=%s rail=%s doc=%s", vector_id, clean["op_rail"], doc[:40])
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
            logger.error("OP 飞轮删除失败: %s", exc, exc_info=True)
            return False

    def bulk_upsert(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """同 document 跳过。"""
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
            payload = entry.get("payload") if isinstance(entry.get("payload"), dict) else {}
            rail = str(payload.get("op_rail") or payload.get("target_type") or "")
            if not doc:
                failed.append({"index": i, "reason": "空 document"})
                continue
            if self._find_id_by_document(doc):
                skipped.append({"index": i, "document": doc})
                continue
            vid = self.add(doc, rail)
            if not vid:
                failed.append({"index": i, "reason": "写入失败或非法 rail"})
                continue
            added += 1
            ids.append(vid)
        return {"ok": added, "added": added, "skipped": skipped, "failed": failed, "ids": ids}


op_cue_store = OpCueStore()
