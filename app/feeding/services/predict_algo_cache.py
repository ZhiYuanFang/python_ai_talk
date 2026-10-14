"""
预测算法 Redis 设备快照

业务说明：
key=predict_algo:{device_no}；TTL 600 秒。
存按 root 的工具 JSON，供连续兜底跳过 7 日重拉与重算。
CUD 落库成功须主动 delete；不写入意图/时间分类飞轮。
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from app.shared.redis_gate import create_async_redis_client

logger = logging.getLogger(__name__)

_KEY_PREFIX = "predict_algo:"
_TTL_SEC = 600


class PredictAlgoCache:
    """设备级算法快照读写。"""

    def __init__(self) -> None:
        self._redis = None

    def _client(self):
        if self._redis is None:
            self._redis = create_async_redis_client()
        return self._redis

    def _key(self, device_no: str) -> str:
        return f"{_KEY_PREFIX}{str(device_no or '').strip()}"

    async def get(self, device_no: str) -> Optional[Dict[str, Any]]:
        """
        读取快照。

        Returns:
            {"by_root": {event_id: tool_dict, ...}, ...} 或 None
        """
        dn = str(device_no or "").strip()
        if not dn:
            return None
        try:
            raw = await self._client().get(self._key(dn))
            if not raw:
                return None
            data = json.loads(raw)
            if not isinstance(data, dict):
                return None
            by_root = data.get("by_root")
            if not isinstance(by_root, dict):
                return None
            return data
        except Exception as exc:
            logger.warning("读预测算法快照失败 device=%s err=%s", dn, exc)
            return None

    async def set(self, device_no: str, by_root: Dict[str, Dict[str, Any]]) -> None:
        """写入/覆盖设备快照（TTL 10 分钟）。"""
        dn = str(device_no or "").strip()
        if not dn:
            return
        payload = {"by_root": by_root or {}}
        try:
            await self._client().set(
                self._key(dn),
                json.dumps(payload, ensure_ascii=False),
                ex=_TTL_SEC,
            )
        except Exception as exc:
            logger.warning("写预测算法快照失败 device=%s err=%s", dn, exc)

    async def delete(self, device_no: str) -> None:
        """CUD 落库后清除快照。"""
        dn = str(device_no or "").strip()
        if not dn:
            return
        try:
            await self._client().delete(self._key(dn))
            logger.info("已清除预测算法快照 device=%s", dn)
        except Exception as exc:
            logger.warning("删预测算法快照失败 device=%s err=%s", dn, exc)

    async def get_root(
        self, device_no: str, root_event_id: str
    ) -> Optional[Dict[str, Any]]:
        """取单根快照条目。"""
        data = await self.get(device_no)
        if not data:
            return None
        by_root = data.get("by_root") or {}
        rid = str(root_event_id or "").strip()
        item = by_root.get(rid)
        return item if isinstance(item, dict) else None

    async def put_root(
        self, device_no: str, root_event_id: str, tool_dict: Dict[str, Any]
    ) -> None:
        """合并写入单根（读-改-写）。"""
        dn = str(device_no or "").strip()
        rid = str(root_event_id or "").strip()
        if not dn or not rid:
            return
        data = await self.get(dn) or {"by_root": {}}
        by_root = dict(data.get("by_root") or {})
        by_root[rid] = tool_dict
        await self.set(dn, by_root)


predict_algo_cache = PredictAlgoCache()
