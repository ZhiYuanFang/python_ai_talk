"""
护理留意飞轮映射（suggestionId → knowledge_ids）

业务说明：
analyze 将本轮进 prompt 的通识文档 id 按 suggestionId 写入 Redis；
feedback 凭 suggestion_id 取回并对 mother_baby_knowledge 加减质量分。
失败降级为空映射，不阻断主流程。
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.config.settings import settings
from app.shared.redis_gate import create_async_redis_client

logger = logging.getLogger(__name__)

_KEY_PREFIX = "care_alert:flywheel:"


class CareAlertFlywheelStore:
    """
    Redis 映射读写。

    key = care_alert:flywheel:{suggestion_id}
    value = JSON {device_no, day, knowledge_ids}
    """

    def __init__(self) -> None:
        self._redis = None

    def _client(self):
        """懒创建与闸门共用的异步 Redis 客户端。"""
        if self._redis is None:
            self._redis = create_async_redis_client()
        return self._redis

    def _key(self, suggestion_id: str) -> str:
        return f"{_KEY_PREFIX}{(suggestion_id or '').strip()}"

    def _ttl_seconds(self) -> int:
        days = max(1, int(getattr(settings, "care_alert_flywheel_ttl_days", 7) or 7))
        return days * 24 * 3600

    async def save_mapping(
        self,
        suggestion_id: str,
        *,
        device_no: str,
        day: str,
        knowledge_ids: List[str],
    ) -> None:
        """
        写入 suggestion → knowledge_ids。

        Args:
            suggestion_id: 留意项 UUID
            device_no: 设备号
            day: 逻辑日
            knowledge_ids: 本轮进 prompt 的通识 doc id
        """
        sid = (suggestion_id or "").strip()
        if not sid:
            return
        payload = {
            "device_no": device_no or "",
            "day": day or "",
            "knowledge_ids": [str(x) for x in (knowledge_ids or []) if x],
        }
        try:
            await self._client().set(
                self._key(sid),
                json.dumps(payload, ensure_ascii=False),
                ex=self._ttl_seconds(),
            )
            logger.info(
                "护理留意飞轮映射已写: suggestion_id=%s kids=%s",
                sid,
                len(payload["knowledge_ids"]),
            )
        except Exception as e:
            logger.warning("护理留意飞轮映射写入失败 suggestion_id=%s: %s", sid, e)

    async def get_knowledge_ids(self, suggestion_id: str) -> List[str]:
        """
        读取映射中的 knowledge_ids；缺失或失败返回 []。

        Args:
            suggestion_id: 留意项 UUID

        Returns:
            文档 id 列表
        """
        sid = (suggestion_id or "").strip()
        if not sid:
            return []
        try:
            raw = await self._client().get(self._key(sid))
            if not raw:
                return []
            data = json.loads(raw)
            if not isinstance(data, dict):
                return []
            ids = data.get("knowledge_ids") or []
            if not isinstance(ids, list):
                return []
            return [str(x) for x in ids if x]
        except Exception as e:
            logger.warning("护理留意飞轮映射读取失败 suggestion_id=%s: %s", sid, e)
            return []


# 全局单例
care_alert_flywheel_store = CareAlertFlywheelStore()


def suggestion_ids_from_items(items: List[Dict[str, Any]]) -> List[str]:
    """从 camelCase items 提取 suggestionId 列表（去重保序）。"""
    out: List[str] = []
    seen = set()
    for item in items or []:
        if not isinstance(item, dict):
            continue
        sid = str(item.get("suggestionId") or item.get("suggestion_id") or "").strip()
        if not sid or sid in seen:
            continue
        seen.add(sid)
        out.append(sid)
    return out
