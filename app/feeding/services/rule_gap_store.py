"""
规则缺口收件箱

业务说明：
仅 TIME/QTY 规则未覆盖且走小 LLM 时落盘，供 Hub 扩规则。
TYPE/EVENT/SHAPE 走飞轮自更新，不进本箱。
JSONL 存于 chroma 同级 data 目录；短窗按 dimension+segment 去重。
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.config.settings import settings

logger = logging.getLogger(__name__)

# 同一维度+段原文去重窗（秒）
_DEDUP_WINDOW_S = 120


class RuleGapStore:
    """规则缺口 JSONL 存储。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # key -> last_ts
        self._recent: Dict[str, float] = {}
        self._path = os.path.join(
            settings.chroma_persist_dir,
            "..",
            "rule_gaps",
            "gaps.jsonl",
        )
        self._path = os.path.normpath(self._path)

    def _ensure_dir(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)

    def _dedupe_key(self, dimension: str, segment_text: str) -> str:
        return f"{(dimension or '').strip()}|{(segment_text or '').strip()}"

    def record(
        self,
        *,
        dimension: str,
        segment_text: str,
        utterance: str,
        reason: str,
        llm_used: bool = False,
        llm_result: str = "",
        device_no: str = "",
        rule_result: str = "",
    ) -> Optional[str]:
        """
        写入一条 open 缺口；短窗重复则跳过。

        Returns:
            新记录 id，或 None（去重跳过）
        """
        dim = (dimension or "").strip() or "unknown"
        seg = (segment_text or "").strip()
        if not seg and not (utterance or "").strip():
            return None
        key = self._dedupe_key(dim, seg or utterance)
        now = time.time()
        with self._lock:
            last = self._recent.get(key)
            if last is not None and now - last < _DEDUP_WINDOW_S:
                logger.info("规则缺口短窗去重: dim=%s seg=%s", dim, seg[:40])
                return None
            self._recent[key] = now
            # 顺带清理过期键
            stale = [k for k, ts in self._recent.items() if now - ts > _DEDUP_WINDOW_S]
            for k in stale:
                self._recent.pop(k, None)

            self._ensure_dir()
            rid = f"gap_{uuid.uuid4().hex}"
            row = {
                "id": rid,
                "dimension": dim,
                "segment_text": seg,
                "utterance": (utterance or "").strip(),
                "reason": (reason or "").strip(),
                "rule_result": (rule_result or "").strip(),
                "llm_used": bool(llm_used),
                "llm_result": (llm_result or "").strip()[:500],
                "device_no": (device_no or "").strip(),
                "status": "open",
                "created_at": datetime.now().isoformat(),
            }
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            logger.info(
                "规则缺口已记: id=%s dim=%s reason=%s seg=%s",
                rid,
                dim,
                reason,
                seg[:40],
            )
            return rid

    def _load_all(self) -> List[Dict[str, Any]]:
        if not os.path.isfile(self._path):
            return []
        rows: List[Dict[str, Any]] = []
        with open(self._path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return rows

    def _rewrite_all(self, rows: List[Dict[str, Any]]) -> None:
        self._ensure_dir()
        with open(self._path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def list_entries(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        dimension: str = "",
        status: str = "open",
    ) -> Dict[str, Any]:
        """分页列表，默认仅 open，新→旧。"""
        rows = self._load_all()
        dim_f = (dimension or "").strip()
        st_f = (status or "").strip()
        if dim_f:
            rows = [r for r in rows if str(r.get("dimension") or "") == dim_f]
        if st_f:
            rows = [r for r in rows if str(r.get("status") or "") == st_f]
        rows.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
        total = len(rows)
        start = max(0, int(offset))
        lim = max(1, min(500, int(limit)))
        items = rows[start : start + lim]
        return {
            "total": total,
            "offset": start,
            "limit": lim,
            "items": items,
        }

    def set_status(self, gap_id: str, status: str) -> bool:
        """更新 status（如 dismissed）；找不到返回 False。"""
        gid = (gap_id or "").strip()
        st = (status or "").strip() or "dismissed"
        if not gid:
            return False
        with self._lock:
            rows = self._load_all()
            found = False
            for row in rows:
                if str(row.get("id") or "") == gid:
                    row["status"] = st
                    found = True
                    break
            if found:
                self._rewrite_all(rows)
            return found


rule_gap_store = RuleGapStore()
