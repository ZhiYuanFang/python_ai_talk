"""
意图插话缓冲与 device 单飞（Redis + 进程内等待）

业务说明：
同 deviceNo 同时仅一轮意图在跑；busy 时后续 text 入 pending，调用方 await 终局。
TTL 600s 防死锁。终局/重跑启动/异常须清 pending；完成时写入 final 供挂起方读取。
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.shared.redis_gate import create_async_redis_client

logger = logging.getLogger(__name__)

_KEY_PREFIX = "intent_barge:"
_TTL_SEC = 600
_MAX_RERUN = 5
_POLL_SEC = 0.15


@dataclass
class BargeSnapshot:
    """单设备匣快照。"""

    busy: bool = False
    anchor_text: str = ""
    pending: List[str] = field(default_factory=list)
    rerun_count: int = 0
    status: str = "idle"  # idle | running | done | error
    final_response: Optional[Dict[str, Any]] = None
    updated_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "busy": self.busy,
            "anchor_text": self.anchor_text,
            "pending": list(self.pending),
            "rerun_count": self.rerun_count,
            "status": self.status,
            "final_response": self.final_response,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "BargeSnapshot":
        pending = raw.get("pending") or []
        if not isinstance(pending, list):
            pending = []
        return cls(
            busy=bool(raw.get("busy")),
            anchor_text=str(raw.get("anchor_text") or ""),
            pending=[str(x) for x in pending if str(x).strip()],
            rerun_count=int(raw.get("rerun_count") or 0),
            status=str(raw.get("status") or "idle"),
            final_response=raw.get("final_response")
            if isinstance(raw.get("final_response"), dict)
            else None,
            updated_at=float(raw.get("updated_at") or 0),
        )


class IntentBargeStore:
    """
    device 级意图单飞与插话匣。

    进程内 Event 唤醒同 worker 挂起方；跨 worker 靠 Redis 轮询 final。
    """

    def __init__(self) -> None:
        self._redis = None
        self._locks: Dict[str, asyncio.Lock] = {}
        self._events: Dict[str, asyncio.Event] = {}

    def _client(self):
        if self._redis is None:
            self._redis = create_async_redis_client()
        return self._redis

    def _key(self, device_no: str) -> str:
        return f"{_KEY_PREFIX}{str(device_no or '').strip()}"

    def _lock(self, device_no: str) -> asyncio.Lock:
        dn = str(device_no or "").strip()
        if dn not in self._locks:
            self._locks[dn] = asyncio.Lock()
        return self._locks[dn]

    def _event(self, device_no: str) -> asyncio.Event:
        dn = str(device_no or "").strip()
        if dn not in self._events:
            self._events[dn] = asyncio.Event()
        return self._events[dn]

    async def _load(self, device_no: str) -> BargeSnapshot:
        dn = str(device_no or "").strip()
        if not dn:
            return BargeSnapshot()
        try:
            raw = await self._client().get(self._key(dn))
            if not raw:
                return BargeSnapshot()
            data = json.loads(raw)
            if not isinstance(data, dict):
                return BargeSnapshot()
            return BargeSnapshot.from_dict(data)
        except Exception as exc:
            logger.warning("读意图 barge 失败 device=%s err=%s", dn, exc)
            return BargeSnapshot()

    async def _save(self, device_no: str, snap: BargeSnapshot) -> None:
        dn = str(device_no or "").strip()
        if not dn:
            return
        snap.updated_at = time.time()
        try:
            await self._client().set(
                self._key(dn),
                json.dumps(snap.to_dict(), ensure_ascii=False),
                ex=_TTL_SEC,
            )
        except Exception as exc:
            logger.warning("写意图 barge 失败 device=%s err=%s", dn, exc)

    async def _delete(self, device_no: str) -> None:
        dn = str(device_no or "").strip()
        if not dn:
            return
        try:
            await self._client().delete(self._key(dn))
        except Exception as exc:
            logger.warning("删意图 barge 失败 device=%s err=%s", dn, exc)

    async def begin_or_enqueue(self, device_no: str, text: str) -> str:
        """
        空闲则占坑开跑；busy 则 text 入 pending。

        Returns:
            "owner" | "waiter"
        """
        dn = str(device_no or "").strip()
        utterance = (text or "").strip()
        if not dn:
            return "owner"
        async with self._lock(dn):
            snap = await self._load(dn)
            if snap.busy and snap.status == "running":
                if utterance:
                    snap.pending.append(utterance)
                await self._save(dn, snap)
                self._event(dn).clear()
                return "waiter"
            # 占坑
            self._event(dn).clear()
            snap = BargeSnapshot(
                busy=True,
                anchor_text=utterance,
                pending=[],
                rerun_count=0,
                status="running",
                final_response=None,
            )
            await self._save(dn, snap)
            return "owner"

    async def wait_for_final(
        self, device_no: str, *, timeout_sec: float = 580.0
    ) -> Optional[Dict[str, Any]]:
        """
        挂起方等待终局 final_response。

        Returns:
            IntentResponse.model_dump 或 None（超时）
        """
        dn = str(device_no or "").strip()
        if not dn:
            return None
        deadline = time.time() + max(1.0, timeout_sec)
        ev = self._event(dn)
        while time.time() < deadline:
            snap = await self._load(dn)
            if snap.status in ("done", "error") and snap.final_response is not None:
                return snap.final_response
            if snap.status in ("done", "error") and not snap.busy:
                return snap.final_response
            try:
                await asyncio.wait_for(ev.wait(), timeout=_POLL_SEC)
            except asyncio.TimeoutError:
                pass
            ev.clear()
        logger.warning("意图 barge 挂起等待超时 device=%s", dn)
        return None

    async def get_snapshot(self, device_no: str) -> BargeSnapshot:
        """读取当前匣。"""
        return await self._load(device_no)

    async def clear_pending(self, device_no: str) -> None:
        """仅清空 pending（重跑前）。"""
        dn = str(device_no or "").strip()
        if not dn:
            return
        async with self._lock(dn):
            snap = await self._load(dn)
            snap.pending = []
            await self._save(dn, snap)

    async def prepare_rerun(self, device_no: str, concatenated: str) -> int:
        """
        拼接后清 pending，更新 anchor，rerun_count+1，保持 busy/running。

        Returns:
            新的 rerun_count
        """
        dn = str(device_no or "").strip()
        async with self._lock(dn):
            snap = await self._load(dn)
            snap.pending = []
            snap.anchor_text = (concatenated or "").strip()
            snap.rerun_count = int(snap.rerun_count or 0) + 1
            snap.status = "running"
            snap.final_response = None
            snap.busy = True
            await self._save(dn, snap)
            return snap.rerun_count

    async def finish_success(
        self, device_no: str, response_dump: Dict[str, Any]
    ) -> None:
        """正常终局：写 final、清 pending、释放 busy，唤醒挂起方。"""
        dn = str(device_no or "").strip()
        if not dn:
            return
        async with self._lock(dn):
            snap = BargeSnapshot(
                busy=False,
                anchor_text="",
                pending=[],
                rerun_count=0,
                status="done",
                final_response=response_dump,
            )
            await self._save(dn, snap)
            self._event(dn).set()

    async def finish_error(self, device_no: str, message: str = "") -> None:
        """异常：清匣并唤醒挂起方。"""
        dn = str(device_no or "").strip()
        if not dn:
            return
        async with self._lock(dn):
            snap = BargeSnapshot(
                busy=False,
                anchor_text="",
                pending=[],
                rerun_count=0,
                status="error",
                final_response={
                    "content": message or "脑电波过载，请稍后重试",
                    "target_type": "other",
                    "need_confirm": False,
                    "merged": True,
                },
            )
            await self._save(dn, snap)
            self._event(dn).set()

    @property
    def max_rerun(self) -> int:
        return _MAX_RERUN


def concat_anchor_and_pending(anchor: str, pending: List[str]) -> str:
    """全量拼接：锚点 + 缓冲，空格连接。"""
    parts: List[str] = []
    a = (anchor or "").strip()
    if a:
        parts.append(a)
    for p in pending or []:
        s = str(p or "").strip()
        if s:
            parts.append(s)
    return " ".join(parts)


intent_barge_store = IntentBargeStore()
