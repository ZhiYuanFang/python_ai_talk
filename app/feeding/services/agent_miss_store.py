"""
智能体覆盖缺口收件箱（答不出）

业务说明：
终局无法识别/暂不支持等失败回复前落盘，供 Hub 查删以发现未覆盖场景。
独立于 rule_gaps 与 feeding_time_cues；JSONL 落在 chroma 持久目录子路径。
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

# 同设备同原话短窗去重（秒）
_DEDUP_WINDOW_S = 120


class AgentMissStore:
    """覆盖缺口 JSONL 存储。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._recent: Dict[str, float] = {}
        self._path = os.path.normpath(
            os.path.join(
                settings.chroma_persist_dir, "agent_miss", "misses.jsonl"
            )
        )

    def _ensure_dir(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)

    def _dedupe_key(self, device_no: str, utterance: str) -> str:
        return f"{(device_no or '').strip()}|{(utterance or '').strip()}"

    def record(
        self,
        *,
        utterance: str,
        reply: str,
        fail_kind: str,
        device_no: str = "",
        conversation_id: str = "",
        extra: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        写入一条 open 覆盖缺口。

        Returns:
            新 id，或 None（去重/空输入跳过）
        """
        utt = (utterance or "").strip()
        rep = (reply or "").strip()
        if not utt and not rep:
            return None
        kind = (fail_kind or "").strip() or "unknown"
        key = self._dedupe_key(device_no, utt or rep)
        now = time.time()
        with self._lock:
            last = self._recent.get(key)
            if last is not None and now - last < _DEDUP_WINDOW_S:
                logger.info("覆盖缺口短窗去重: kind=%s utt=%s", kind, utt[:40])
                return None
            self._recent[key] = now
            stale = [
                k for k, ts in self._recent.items() if now - ts > _DEDUP_WINDOW_S
            ]
            for k in stale:
                self._recent.pop(k, None)

            self._ensure_dir()
            rid = f"miss_{uuid.uuid4().hex}"
            row: Dict[str, Any] = {
                "id": rid,
                "utterance": utt,
                "reply": rep[:1000],
                "fail_kind": kind,
                "device_no": (device_no or "").strip(),
                "conversation_id": (conversation_id or "").strip(),
                "status": "open",
                "created_at": datetime.now().isoformat(),
            }
            if extra and isinstance(extra, dict):
                row["extra"] = extra
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            logger.info(
                "覆盖缺口已记: id=%s kind=%s utt=%s",
                rid,
                kind,
                utt[:40],
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
        status: str = "open",
        fail_kind: str = "",
    ) -> Dict[str, Any]:
        """分页列表，默认仅 open，新→旧。"""
        rows = self._load_all()
        st_f = (status or "").strip()
        kind_f = (fail_kind or "").strip()
        if st_f:
            rows = [r for r in rows if str(r.get("status") or "") == st_f]
        if kind_f:
            rows = [r for r in rows if str(r.get("fail_kind") or "") == kind_f]
        rows.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
        total = len(rows)
        start = max(0, int(offset))
        lim = max(1, min(500, int(limit)))
        return {
            "total": total,
            "offset": start,
            "limit": lim,
            "items": rows[start : start + lim],
        }

    def delete_by_id(self, miss_id: str) -> bool:
        """物理删除一条；找不到返回 False。"""
        mid = (miss_id or "").strip()
        if not mid:
            return False
        with self._lock:
            rows = self._load_all()
            kept = [r for r in rows if str(r.get("id") or "") != mid]
            if len(kept) == len(rows):
                return False
            self._rewrite_all(kept)
            return True


agent_miss_store = AgentMissStore()
