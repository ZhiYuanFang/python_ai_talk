"""
规则缺口收件箱

业务说明：
各维本地规则未覆盖时落盘（飞轮命中或小模型都记），供 Hub 扩规则。
JSONL 落在 CHROMA_PERSIST_DIR 子目录 rule_gaps/，与 Docker chroma 卷同命运；
短窗按 dimension+segment 去重。open 记录仅人工 dismissed，启动不清箱。
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.config.settings import settings

logger = logging.getLogger(__name__)

# 同一维度+段原文去重窗（秒）
_DEDUP_WINDOW_S = 120


def _file_nonempty(path: str) -> bool:
    """文件存在且字节数 > 0。"""
    try:
        return os.path.isfile(path) and os.path.getsize(path) > 0
    except OSError:
        return False


class RuleGapStore:
    """规则缺口 JSONL 存储（权威路径在 chroma 持久目录内）。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # key -> last_ts（进程内短窗去重，重启可丢）
        self._recent: Dict[str, float] = {}
        # 与 compose 挂载的 chroma 卷同前缀，重建容器不丢
        self._path = os.path.normpath(
            os.path.join(settings.chroma_persist_dir, "rule_gaps", "gaps.jsonl")
        )
        # 旧版误写到卷外兄弟目录，升级时一次性迁入
        self._legacy_path = os.path.normpath(
            os.path.join(settings.chroma_persist_dir, "..", "rule_gaps", "gaps.jsonl")
        )
        self._migrate_legacy_if_needed()

    def _ensure_dir(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)

    def _migrate_legacy_if_needed(self) -> None:
        """
        旧路径有内容且新路径为空时迁入；失败只打日志。
        新路径已有内容则绝不覆盖。
        """
        try:
            if _file_nonempty(self._path):
                if _file_nonempty(self._legacy_path):
                    logger.warning(
                        "规则缺口新旧路径均有内容，跳过迁移: new=%s old=%s",
                        self._path,
                        self._legacy_path,
                    )
                return
            if not _file_nonempty(self._legacy_path):
                return
            self._ensure_dir()
            shutil.move(self._legacy_path, self._path)
            logger.info(
                "规则缺口已从旧路径迁入: %s -> %s",
                self._legacy_path,
                self._path,
            )
        except Exception as exc:
            logger.error("规则缺口旧路径迁移失败: %s", exc, exc_info=True)

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
