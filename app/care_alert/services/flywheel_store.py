"""
护理留意飞轮映射（suggestionId → 建议快照）

业务说明：
analyze 将本轮每条留意项的归因快照按 suggestionId 写入 Redis；
feedback 凭 suggestion_id 取回快照，写入本地 ledger 并驱动 prompt 对比样例飞轮。
失败降级为空，不阻断主流程。不再映射 knowledge_ids / 不通识质量分。
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.config.settings import settings
from app.shared.redis_gate import create_async_redis_client

logger = logging.getLogger(__name__)

_KEY_PREFIX = "care_alert:flywheel:"


def score_band_from_reasons(reasons: Any) -> str:
    """
    由 reasons 推断信号档：强 / 弱。

    业务逻辑：
    任一 reason score>=0.7 或 expectationUsed=true → strong，否则 weak。
    """
    if not isinstance(reasons, list):
        return "weak"
    for r in reasons:
        if not isinstance(r, dict):
            continue
        try:
            score = float(r.get("score") if r.get("score") is not None else 0.0)
        except (TypeError, ValueError):
            score = 0.0
        expectation = r.get("expectationUsed", r.get("expectation_used"))
        used = expectation is True or str(expectation).lower() in ("true", "1")
        if score >= 0.7 or used:
            return "strong"
    return "weak"


def primary_reason_type(reasons: Any) -> str:
    """取首条 reason.type，缺省 other。"""
    if not isinstance(reasons, list):
        return "other"
    for r in reasons:
        if isinstance(r, dict):
            t = str(r.get("type") or "").strip()
            if t:
                return t
    return "other"


def snapshot_from_item(
    item: Dict[str, Any],
    *,
    device_no: str,
    day: str,
) -> Dict[str, Any]:
    """
    从 camelCase item 构建反馈归因快照。

    Args:
        item: analyze 产出的单条 item
        device_no: 设备号
        day: 逻辑日

    Returns:
        可 JSON 序列化的快照 dict
    """
    reasons = item.get("reasons") or []
    summary = str(item.get("summaryLine") or item.get("summary_line") or "").strip()
    if len(summary) > 80:
        summary = summary[:80] + "…"
    return {
        "device_no": device_no or "",
        "day": day or "",
        "event_id": str(item.get("eventId") or item.get("event_id") or "").strip(),
        "event_name": str(item.get("eventName") or item.get("event_name") or "").strip(),
        "reason_type": primary_reason_type(reasons),
        "score_band": score_band_from_reasons(reasons),
        "summary_line": summary,
    }


class CareAlertFlywheelStore:
    """
    Redis 建议快照读写。

    key = care_alert:flywheel:{suggestion_id}
    value = JSON 快照（非 knowledge_ids）
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

    async def save_snapshot(
        self,
        suggestion_id: str,
        snapshot: Dict[str, Any],
    ) -> None:
        """
        写入 suggestion → 快照。

        Args:
            suggestion_id: 留意项 UUID
            snapshot: 归因快照
        """
        sid = (suggestion_id or "").strip()
        if not sid:
            return
        payload = dict(snapshot or {})
        try:
            await self._client().set(
                self._key(sid),
                json.dumps(payload, ensure_ascii=False),
                ex=self._ttl_seconds(),
            )
            logger.info(
                "护理留意飞轮快照已写: suggestion_id=%s type=%s band=%s",
                sid,
                payload.get("reason_type"),
                payload.get("score_band"),
            )
        except Exception as e:
            logger.warning("护理留意飞轮快照写入失败 suggestion_id=%s: %s", sid, e)

    async def get_snapshot(self, suggestion_id: str) -> Optional[Dict[str, Any]]:
        """
        读取建议快照；缺失或失败返回 None。

        Args:
            suggestion_id: 留意项 UUID

        Returns:
            快照 dict 或 None
        """
        sid = (suggestion_id or "").strip()
        if not sid:
            return None
        try:
            raw = await self._client().get(self._key(sid))
            if not raw:
                return None
            data = json.loads(raw)
            if not isinstance(data, dict):
                return None
            # 兼容旧 knowledge_ids 映射：视为无效快照
            if "knowledge_ids" in data and "reason_type" not in data and "event_name" not in data:
                return None
            return data
        except Exception as e:
            logger.warning("护理留意飞轮快照读取失败 suggestion_id=%s: %s", sid, e)
            return None


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
