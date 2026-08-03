"""
陪伴会话存储（tip / clinic 共享）

业务说明：
按 device_no 在 Redis 中维护近 N 轮 user+assistant 对话（默认 3 轮，可配置），
TTL 7 天滑动续期。tip 开场与 clinic 续聊读写同一会话，供口语化闺蜜上下文与隐式飞轮使用。

设计思路：
1. key = companion:session:{device_no}
2. 一轮 = user + assistant；tip 开场合成 user「刚记录了「事件」」
3. 截断只保留最近 max_turns 整轮（与注入 chat_context 一致，默认 3）
4. last_suggestion 记录待隐式判定的建议与 knowledge_ids（与进 prompt 的 knowledge 对齐）
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from app.config.settings import settings
from app.shared.redis_gate import create_async_redis_client

logger = logging.getLogger(__name__)

# Redis key 前缀
_KEY_PREFIX = "companion:session:"


@dataclass
class CompanionTurn:
    """一轮对话：家长一句 + 闺蜜一句。"""

    user: str
    assistant: str
    source: str = ""  # tip | clinic


@dataclass
class LastSuggestion:
    """
    上一条待飞轮判定的建议。

    feedback_applied=True 后不再对同一条加减分。
    standalone_question / age_band 供 accepted 时写入全局 Q&A。
    """

    answer_id: str = ""
    text: str = ""
    knowledge_ids: List[str] = field(default_factory=list)
    feedback_applied: bool = False
    source: str = ""  # tip | clinic
    standalone_question: str = ""
    age_band: str = ""


@dataclass
class CompanionSession:
    """单设备陪伴会话。"""

    device_no: str
    turns: List[CompanionTurn] = field(default_factory=list)
    last_suggestion: Optional[LastSuggestion] = None
    updated_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """序列化为可 JSON 的字典。"""
        return {
            "device_no": self.device_no,
            "turns": [asdict(t) for t in self.turns],
            "last_suggestion": asdict(self.last_suggestion)
            if self.last_suggestion
            else None,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompanionSession":
        """从 Redis JSON 反序列化。"""
        turns = [
            CompanionTurn(
                user=str(t.get("user", "")),
                assistant=str(t.get("assistant", "")),
                source=str(t.get("source", "")),
            )
            for t in (data.get("turns") or [])
            if isinstance(t, dict)
        ]
        raw_sug = data.get("last_suggestion")
        last_suggestion = None
        if isinstance(raw_sug, dict):
            last_suggestion = LastSuggestion(
                answer_id=str(raw_sug.get("answer_id", "")),
                text=str(raw_sug.get("text", "")),
                knowledge_ids=[
                    str(x) for x in (raw_sug.get("knowledge_ids") or []) if x
                ],
                feedback_applied=bool(raw_sug.get("feedback_applied", False)),
                source=str(raw_sug.get("source", "")),
                standalone_question=str(raw_sug.get("standalone_question", "")),
                age_band=str(raw_sug.get("age_band", "")),
            )
        return cls(
            device_no=str(data.get("device_no", "")),
            turns=turns,
            last_suggestion=last_suggestion,
            updated_at=float(data.get("updated_at") or 0),
        )


def extract_knowledge_ids(knowledge: Any) -> List[str]:
    """
    从向量检索结果提取真实文档 id（chunk id）。

    业务逻辑：
    优先 item["id"]；其次 metadata.doc_id。去重保序。
    """
    if not knowledge or not isinstance(knowledge, list):
        return []
    ids: List[str] = []
    seen = set()
    for item in knowledge:
        if not isinstance(item, dict):
            continue
        kid = item.get("id")
        if not kid:
            meta = item.get("metadata") or {}
            if isinstance(meta, dict):
                kid = meta.get("doc_id") or meta.get("id")
        if not kid:
            continue
        kid_s = str(kid)
        if kid_s in seen:
            continue
        seen.add(kid_s)
        ids.append(kid_s)
    return ids


def format_chat_turns_for_prompt(turns: List[CompanionTurn]) -> str:
    """
    将会话轮次格式化为提示词中的「近期对话」块。

    与喂养 history_events 分离，仅作闺蜜续聊上下文。
    """
    if not turns:
        return ""
    lines: List[str] = ["近期陪伴对话（从旧到新）："]
    for i, turn in enumerate(turns, start=1):
        lines.append(f"第{i}轮-家长：{turn.user}")
        lines.append(f"第{i}轮-闺蜜：{turn.assistant}")
    return "\n".join(lines)


def build_tip_synthetic_user(event_name: str) -> str:
    """tip 开场合成的家长侧用户文案，保证一轮结构完整。"""
    name = (event_name or "一件事").strip() or "一件事"
    return f"刚记录了「{name}」"


class CompanionSessionStore:
    """
    Redis 陪伴会话读写。

    业务说明：
    tip/clinic 路由共用；失败时降级为空会话，不阻断主流程。
    """

    def __init__(self) -> None:
        self._redis = None

    def _client(self):
        """懒创建 Redis 客户端。"""
        if self._redis is None:
            self._redis = create_async_redis_client()
        return self._redis

    def _key(self, device_no: str) -> str:
        return f"{_KEY_PREFIX}{device_no}"

    def _ttl_seconds(self) -> int:
        days = max(1, int(settings.companion_session_ttl_days))
        return days * 24 * 3600

    def _max_turns(self) -> int:
        return max(1, int(settings.companion_session_max_turns))

    async def get(self, device_no: str) -> CompanionSession:
        """
        读取会话；不存在或失败时返回空会话（不续期，由写路径续期）。
        """
        if not device_no:
            return CompanionSession(device_no=device_no or "")
        try:
            raw = await self._client().get(self._key(device_no))
            if not raw:
                return CompanionSession(device_no=device_no)
            data = json.loads(raw)
            if not isinstance(data, dict):
                return CompanionSession(device_no=device_no)
            session = CompanionSession.from_dict(data)
            session.device_no = device_no
            return session
        except Exception as e:
            logger.warning(f"读取陪伴会话失败 device_no={device_no}: {e}")
            return CompanionSession(device_no=device_no)

    async def save(self, session: CompanionSession) -> None:
        """写入会话并滑动续期 TTL。"""
        if not session.device_no:
            return
        session.updated_at = time.time()
        # 截断到最近 N 轮
        max_turns = self._max_turns()
        if len(session.turns) > max_turns:
            session.turns = session.turns[-max_turns:]
        try:
            key = self._key(session.device_no)
            payload = json.dumps(session.to_dict(), ensure_ascii=False)
            client = self._client()
            await client.set(key, payload, ex=self._ttl_seconds())
        except Exception as e:
            logger.warning(
                f"写入陪伴会话失败 device_no={session.device_no}: {e}"
            )

    async def append_turn(
        self,
        device_no: str,
        *,
        user: str,
        assistant: str,
        source: str,
        answer_id: str,
        knowledge_ids: Optional[List[str]] = None,
        suggestion_text: Optional[str] = None,
        standalone_question: Optional[str] = None,
        age_band: Optional[str] = None,
    ) -> CompanionSession:
        """
        追加一轮并更新 last_suggestion（新建议默认未飞轮）。

        Args:
            device_no: 设备号
            user: 家长侧文本
            assistant: 闺蜜侧全文
            source: tip | clinic
            answer_id: 本轮回答 id
            knowledge_ids: 本轮检索命中的文档 id
            suggestion_text: 待判定建议文本，默认用 assistant
            standalone_question: 本轮改写独立问句（供 Q&A 推广）
            age_band: 本轮月龄带
        """
        session = await self.get(device_no)
        session.turns.append(
            CompanionTurn(user=user or "", assistant=assistant or "", source=source)
        )
        session.last_suggestion = LastSuggestion(
            answer_id=answer_id or "",
            text=(suggestion_text if suggestion_text is not None else assistant) or "",
            knowledge_ids=list(knowledge_ids or []),
            feedback_applied=False,
            source=source,
            standalone_question=(standalone_question or "").strip(),
            age_band=(age_band or "").strip(),
        )
        await self.save(session)
        return session

    async def mark_feedback_applied(self, device_no: str) -> None:
        """将 last_suggestion.feedback_applied 置 True 并写回。"""
        session = await self.get(device_no)
        if not session.last_suggestion:
            return
        session.last_suggestion.feedback_applied = True
        await self.save(session)


# 全局单例，供 tip/clinic 路由使用
companion_session_store = CompanionSessionStore()
