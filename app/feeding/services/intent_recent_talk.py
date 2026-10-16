"""
意图侧最近十分钟对话

业务说明：
按设备记下家长听到的原话和回答，只给漏答自由回答当背景。
与诊疗陪伴会话分开。超过十分钟的轮次丢掉。Redis 失败不阻断主回答。
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List

from app.shared.redis_gate import create_async_redis_client

logger = logging.getLogger(__name__)

_KEY_PREFIX = "intent:recent_talk:"
# 窗口与键过期都是十分钟
WINDOW_SEC = 600
# 注入提示词的整段上限；放不下就丢更早的轮
PROMPT_BUDGET = 800
# 单侧过长只留前一段，避免一轮占满预算
_SIDE_CAP = 200


def _clip(text: str) -> str:
    """单侧截到前一段。"""
    raw = (text or "").strip()
    if len(raw) <= _SIDE_CAP:
        return raw
    return raw[:_SIDE_CAP]


def format_recent_dialogue(turns: List[Dict[str, Any]], *, budget: int = PROMPT_BUDGET) -> str:
    """
    从新到旧装进预算，再按时间顺序输出。

    装不下的更早轮次直接不要。一轮本身超过预算时只留这一轮的前一段。
    """
    chosen: List[str] = []
    total = 0
    for turn in reversed(turns):
        if not isinstance(turn, dict):
            continue
        piece = f"家长：{_clip(str(turn.get('user') or ''))}\n回答：{_clip(str(turn.get('assistant') or ''))}"
        extra = len(piece) + (1 if chosen else 0)
        if chosen and total + extra > budget:
            break
        if not chosen and len(piece) > budget:
            piece = piece[:budget]
            extra = len(piece)
        chosen.append(piece)
        total += extra
    chosen.reverse()
    return "\n".join(chosen)


class IntentRecentTalkStore:
    """设备级短时对话。键 intent:recent_talk:{device_no}。"""

    def __init__(self) -> None:
        self._redis = None

    def _client(self):
        if self._redis is None:
            self._redis = create_async_redis_client()
        return self._redis

    def _key(self, device_no: str) -> str:
        return f"{_KEY_PREFIX}{device_no}"

    async def load_recent(self, device_no: str) -> List[Dict[str, Any]]:
        """读取仍在十分钟内的轮次。失败返回空列表。"""
        if not device_no:
            return []
        now = time.time()
        try:
            raw = await self._client().get(self._key(device_no))
        except Exception as exc:
            logger.warning("读取意图近况失败 device_no=%s: %s", device_no, exc)
            return []
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return []
        turns = data.get("turns") if isinstance(data, dict) else None
        if not isinstance(turns, list):
            return []
        kept: List[Dict[str, Any]] = []
        for turn in turns:
            if not isinstance(turn, dict):
                continue
            try:
                at = float(turn.get("at") or 0)
            except (TypeError, ValueError):
                continue
            if now - at > WINDOW_SEC:
                continue
            user = str(turn.get("user") or "").strip()
            assistant = str(turn.get("assistant") or "").strip()
            if not user or not assistant:
                continue
            kept.append({"user": user, "assistant": assistant, "at": at})
        return kept

    async def prompt_block(self, device_no: str) -> str:
        """给漏答提示词的近况段。没有则空串。"""
        turns = await self.load_recent(device_no)
        return format_recent_dialogue(turns)

    async def append_turn(self, device_no: str, *, user: str, assistant: str) -> None:
        """
        追加一轮并刷新十分钟过期。

        空回答不记。失败只打日志。
        """
        utterance = (user or "").strip()
        spoken = (assistant or "").strip()
        if not device_no or not utterance or not spoken:
            return
        now = time.time()
        turns = await self.load_recent(device_no)
        turns.append({"user": utterance, "assistant": spoken, "at": now})
        payload = json.dumps({"turns": turns}, ensure_ascii=False)
        try:
            await self._client().set(self._key(device_no), payload, ex=WINDOW_SEC)
        except Exception as exc:
            logger.warning("写入意图近况失败 device_no=%s: %s", device_no, exc)


intent_recent_talk_store = IntentRecentTalkStore()
