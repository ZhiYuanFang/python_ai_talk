"""
事件短说法向量库（原意图整包缓存）

业务说明：
独立 Collection feeding_intents，document 为单事件短说法/别名，
payload 仅含 event_id / event_name / kind（parent|leaf）。
禁止再写入或回放整包 multi-events 意图。
确认落库后按段写入；管理端 bulk 灌种子。
相似度门槛 0.72；「嗯/是的」等不得当 document。
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

# 事件短说法高置信门槛（与规格一致）
INTENT_CACHE_HIGH_THRESHOLD = 0.72
EVENT_PHRASE_THRESHOLD = INTENT_CACHE_HIGH_THRESHOLD
# 质量分下限；缺省按 0.8（管理端列表/清理仍用）
INTENT_CACHE_QUALITY_MIN = 0.7
INTENT_CACHE_QUALITY_DEFAULT = 0.8
INTENT_CACHE_QUALITY_PENALTY = 0.2
INTENT_CACHE_CLEANUP_THRESHOLD = 0.3
# 遗留：短窗重复扣分（整包免确认已废，保留 API 兼容）
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


def _as_event_phrase_payload(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    将写入载荷规范为事件说法形；整包 events 意图拒绝写入。

    Returns:
        {event_id, event_name, kind} 或 None（不可写入）
    """
    if not isinstance(payload, dict):
        return None
    # 显式整包意图：有非空 events 且超过「单事件镜像」则拒
    events = payload.get("events")
    if isinstance(events, list) and len(events) > 1:
        return None
    if isinstance(events, list) and len(events) == 1 and isinstance(events[0], dict):
        ev = events[0]
        eid = str(ev.get("event_id") or payload.get("event_id") or "").strip()
        ename = str(ev.get("event_name") or payload.get("event_name") or "").strip()
        kind = str(payload.get("kind") or "leaf").strip() or "leaf"
        if eid:
            return {"event_id": eid, "event_name": ename, "kind": kind}
        return None
    eid = str(payload.get("event_id") or "").strip()
    ename = str(payload.get("event_name") or "").strip()
    kind = str(payload.get("kind") or "leaf").strip() or "leaf"
    if not eid:
        return None
    if kind not in ("leaf", "parent"):
        kind = "leaf"
    return {"event_id": eid, "event_name": ename, "kind": kind}


class IntentCacheStore:
    """
    事件短说法向量库（Collection 名仍为 feeding_intents）。

    业务说明：
    与知识库 Collection 物理隔离；供段级事件维检索，不回放整包意图。
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
                metadata={"description": "喂养事件短说法飞轮"},
            )
            self._initialized = True
            logger.info("事件短说法向量库初始化完成")

    def _embed(self, texts: List[str]) -> List[List[float]]:
        return self._embedding_model.encode(texts).tolist()

    @staticmethod
    def _document_key(document: str) -> str:
        """
        管理端判重键：去首尾空白后的原文。

        业务说明：
        与 `_find_id_by_document` / 写入前 strip 一致；不做标点或近义归一化。
        """
        return (document or "").strip()

    def _find_id_by_document(self, doc: str) -> Optional[str]:
        """按 document 原文（strip 后全等）找已有 id，避免 uuid 分身绕开扣分。"""
        key = self._document_key(doc)
        if not key:
            return None
        data = self._collection.get(include=["documents"])
        docs = data.get("documents") or []
        ids = data.get("ids") or []
        for i, existing in enumerate(docs):
            # 库内可能存已 strip 的文案；两侧都按 key 比，避免空白分身
            if self._document_key(existing or "") == key:
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
        写入或更新一条事件短说法。

        业务逻辑：
        确认词不写；仅接受 event_id(+name/kind)；拒绝整包 multi-events。
        同一 document 更新并重置质量分为 0.8。
        """
        self._ensure_initialized()
        doc = (document or "").strip()
        if not doc or _is_confirm_only(doc):
            logger.info("跳过事件说法写入：空句或确认词")
            return None
        clean = _as_event_phrase_payload(payload)
        if not clean:
            logger.info(
                "跳过事件说法写入：非短说法载荷或整包 events doc=%s",
                doc[:40],
            )
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
                "更新事件说法: id=%s, doc=%s, event_id=%s",
                existing_id,
                doc[:40],
                clean.get("event_id"),
            )
            return existing_id
        vector_id = f"intent_{uuid.uuid4().hex}"
        self._collection.add(
            ids=[vector_id],
            embeddings=[embedding],
            documents=[doc],
            metadatas=[meta],
        )
        logger.info(
            "写入事件说法: id=%s, doc=%s, event_id=%s",
            vector_id,
            doc[:40],
            clean.get("event_id"),
        )
        return vector_id

    def add_event_phrase(
        self,
        document: str,
        *,
        event_id: str,
        event_name: str = "",
        kind: str = "leaf",
    ) -> Optional[str]:
        """段确认后写入短说法 → 事件。"""
        return self.add(
            document,
            {
                "event_id": str(event_id or "").strip(),
                "event_name": str(event_name or "").strip(),
                "kind": kind if kind in ("leaf", "parent") else "leaf",
            },
        )

    def search_event_phrase(
        self, query: str, n_results: int = 1
    ) -> List[Dict[str, Any]]:
        """
        检索最相似短说法；调用方用 EVENT_PHRASE_THRESHOLD 过滤。

        Returns:
            含 score、document、payload(event_id/name/kind)、id 的列表
        """
        hits = self.search(query, n_results=n_results)
        # 打对照日志便于灌种排查
        if hits:
            top = hits[0]
            logger.info(
                "事件说法检索: query=%s, document=%s, score=%s, event_id=%s, id=%s",
                (query or "")[:80],
                str(top.get("document") or "")[:80],
                top.get("score"),
                (top.get("payload") or {}).get("event_id"),
                top.get("id"),
            )
        return hits

    def list_entries(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        分页列出意图缓存（管理端）。

        业务逻辑：
        全量取出后按 metadata.created_at **新→旧**排序，再 offset/limit 切片。
        created_at 为最近写入时间（add/update 都会刷新）；空字符串沉底；
        同分以 id 字典序升序打破平局（先排 id、再降序 created_at，依赖稳定排序）。

        Returns:
            {total, offset, limit, items:[{id, document, quality_score, payload, created_at}]}
        """
        self._ensure_initialized()
        data = self._collection.get(include=["documents", "metadatas"])
        ids = data.get("ids") or []
        docs = data.get("documents") or []
        metas = data.get("metadatas") or []
        total = len(ids)
        # 先组装全部条目，避免按 Chroma 原序切片导致跨页时间乱序
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
        # 平局：id 升序；再按 created_at 降序（"" 最小，reverse 后沉底）
        all_items.sort(key=lambda x: str(x.get("id") or ""))
        all_items.sort(
            key=lambda x: str(x.get("created_at") or ""),
            reverse=True,
        )
        start = max(0, int(offset))
        page_limit = max(1, min(int(limit), 500))
        end = start + page_limit
        items = all_items[start:end]
        return {
            "total": total,
            "offset": start,
            "limit": page_limit,
            "items": items,
        }

    def delete_by_id(self, vector_id: str) -> bool:
        """按向量 id 删除一条；不存在则 False。"""
        self._ensure_initialized()
        vid = (vector_id or "").strip()
        if not vid:
            return False
        try:
            existing = self._collection.get(ids=[vid], include=[])
            found = existing.get("ids") or []
            if not found:
                logger.warning("意图缓存删除跳过：找不到 id=%s", vid)
                return False
            self._collection.delete(ids=[vid])
            logger.info("已删除意图缓存: id=%s", vid)
            return True
        except Exception as exc:
            logger.error("意图缓存删除失败: %s", exc, exc_info=True)
            return False

    def dedupe_exact_documents(self) -> Dict[str, Any]:
        """
        管理端整理：document 全等分组，每组只留一条，删其余。

        业务逻辑：
        保留规则 — 较高 quality_score；同分较早 created_at；再同分较小 id。
        不写 MySQL；不改运行时 add 覆盖语义。

        Returns:
            {kept, deleted:[{id,document,quality_score}], groups}
        """
        self._ensure_initialized()
        data = self._collection.get(include=["documents", "metadatas"])
        ids = data.get("ids") or []
        docs = data.get("documents") or []
        metas = data.get("metadatas") or []

        # key -> 候选列表
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
            created_at = str(meta.get("created_at") or "")
            groups.setdefault(key, []).append(
                {
                    "id": vid,
                    "document": doc,
                    "quality_score": quality,
                    "created_at": created_at,
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
            # 质量高优先；同分 created_at 升序（早优先）；再比 id
            members_sorted = sorted(
                members,
                key=lambda m: (
                    -float(m.get("quality_score") or 0),
                    str(m.get("created_at") or ""),
                    str(m.get("id") or ""),
                ),
            )
            winner = members_sorted[0]
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
                else:
                    logger.warning("整理重复删除失败: id=%s key=%s", vid, key[:40])

        logger.info(
            "意图缓存整理重复: groups=%s deleted=%s kept_unique=%s",
            dup_groups,
            len(deleted),
            kept,
        )
        return {
            "kept": kept,
            "deleted": deleted,
            "groups": dup_groups,
        }

    def bulk_upsert(
        self, entries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        管理端批量灌种：每项 {document, payload}。

        业务逻辑：
        库中或本批已见相同 document（strip 全等）则跳过，不覆盖 payload/质量分；
        新文案才写入。确认词/空句计入 failed。运行时 add 仍可覆盖同句。

        Returns:
            {ok, added, skipped:[{index,document,existing_id}], failed, ids}
        """
        self._ensure_initialized()
        added = 0
        ids: List[str] = []
        failed: List[Dict[str, Any]] = []
        skipped: List[Dict[str, Any]] = []
        # 本批已处理过的判重键 → 已有/刚写入的 id
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
                    failed.append({"index": i, "reason": "空句或确认词，未写入"})
                    continue
                added += 1
                ids.append(vid)
                seen[doc] = vid
            except Exception as exc:
                logger.error("bulk_upsert 第 %s 条失败: %s", i, exc, exc_info=True)
                failed.append({"index": i, "reason": str(exc)})
        return {
            "ok": added,
            "added": added,
            "skipped": skipped,
            "failed": failed,
            "ids": ids,
        }

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
            metadata={"description": "喂养事件短说法飞轮"},
        )
        logger.warning("已按开关清空事件说法 Collection feeding_intents")

    def migrate_legacy_remark_keys(self) -> Dict[str, int]:
        """
        启动一次性：把 payload 里旧备注 JSON 键迁到 remark（仅本 Collection）。

        业务逻辑：
        顶层与 events[]：旧键非空且 remark 空 → 写入 remark；凡有旧键则删除。
        不覆盖已有非空 remark；不写 MySQL。

        Returns:
            {scanned, updated, filled} 扫描条数 / 改写 metadata 条数 / 实际回填次数
        """
        self._ensure_initialized()
        data = self._collection.get(include=["metadatas"])
        ids = data.get("ids") or []
        metas = data.get("metadatas") or []
        scanned = len(ids)
        updated = 0
        filled = 0
        for i, vid in enumerate(ids):
            meta = dict(metas[i] or {})
            raw = meta.get("payload") or "{}"
            try:
                payload = json.loads(raw) if isinstance(raw, str) else dict(raw or {})
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            new_payload, n_fill, touched = _migrate_payload_legacy_remark(payload)
            if not touched:
                continue
            filled += n_fill
            meta["payload"] = json.dumps(new_payload, ensure_ascii=False)
            try:
                self._collection.update(ids=[vid], metadatas=[meta])
                updated += 1
            except Exception as exc:
                logger.error(
                    "意图缓存备注键迁移失败: id=%s err=%s", vid, exc, exc_info=True
                )
        logger.warning(
            "意图缓存备注键迁移完成: scanned=%s updated=%s filled=%s；"
            "请将 MIGRATE_INTENT_REMARK_KEYWORD_ON_STARTUP 改回 false",
            scanned,
            updated,
            filled,
        )
        return {"scanned": scanned, "updated": updated, "filled": filled}


# 仅启动迁移可读删的旧 JSON 键（运行时意图路径不得再读此键）
_LEGACY_REMARK_JSON_KEY = "remark_keyword"


def _migrate_one_level_legacy_remark(obj: Dict[str, Any]) -> tuple[int, bool]:
    """
    单层 dict：旧键→空 remark，并删除旧键。

    Returns:
        (回填次数 0|1, 是否改动)
    """
    if _LEGACY_REMARK_JSON_KEY not in obj:
        return 0, False
    legacy = str(obj.get(_LEGACY_REMARK_JSON_KEY) or "").strip()
    current = str(obj.get("remark") or "").strip()
    filled = 0
    if legacy and not current:
        obj["remark"] = legacy
        filled = 1
    obj.pop(_LEGACY_REMARK_JSON_KEY, None)
    return filled, True


def _migrate_payload_legacy_remark(
    payload: Dict[str, Any],
) -> tuple[Dict[str, Any], int, bool]:
    """
    迁移整份意图缓存 payload。

    Returns:
        (新 payload, 回填次数, 是否有任何改动)
    """
    out = dict(payload)
    filled = 0
    touched = False
    n, ch = _migrate_one_level_legacy_remark(out)
    filled += n
    touched = touched or ch
    events_in = out.get("events") or []
    if isinstance(events_in, list):
        new_events: List[Any] = []
        events_touched = False
        for ev in events_in:
            if not isinstance(ev, dict):
                new_events.append(ev)
                continue
            item = dict(ev)
            n, ch = _migrate_one_level_legacy_remark(item)
            filled += n
            if ch:
                events_touched = True
            new_events.append(item)
        if events_touched:
            out["events"] = new_events
            touched = True
    return out, filled, touched


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


def _strip_create_absolute_times(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    剥离 create 骨架上的绝对 start/end，避免冻死某次确认时刻。

    业务说明：数量可保留；读窗字段保留。
    """
    out = dict(payload or {})
    events = []
    for ev in out.get("events") or []:
        if not isinstance(ev, dict):
            continue
        item = dict(ev)
        op = str(item.get("op") or "").strip().lower()
        if op == "create":
            item["start_time"] = None
            item["end_time"] = None
        events.append(item)
    out["events"] = events
    return out


intent_cache_store = IntentCacheStore()
