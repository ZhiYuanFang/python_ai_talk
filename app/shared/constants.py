"""
共享协议枚举常量

业务说明：
统一定义意图分析、向量存储、澄清管线对外/对内使用的英文协议枚举值，
保证 IntentResponse、向量 metadata 等输出格式一致。本模块不含中文 label。
"""

from __future__ import annotations

from enum import Enum


class IntentAction(str, Enum):
    """意图响应 / 喂养动作（IntentResponse.action）。"""

    START = "start"
    END = "end"
    ONE = "one"
    SEARCH = "search"
    SUGGESTION = "suggestion"
    REPLY = "reply"
    EXIT = "exit"
    MULTI = "multi"


class TargetType(str, Enum):
    """意图目标类型（IntentResponse.target_type）。"""

    FEEDING = "feeding"
    HISTORY = "history"
    SUGGEST = "suggest"
    CONVERSATION = "conversation"
    EXIT = "exit"


class MatchSource(str, Enum):
    """匹配来源。"""

    VECTOR = "vector"
    LLM = "llm"
    NAME = "name"


class VectorSource(str, Enum):
    """喂养事件向量记录来源。"""

    STANDARD = "standard"
    USER = "user"


class ConfirmType(str, Enum):
    """澄清类型（IntentResponse.confirm_type / pending.kind）。"""

    PARENT_DISAMBIGUATION = "parent_disambiguation"
    LEAF_CONFIRM = "leaf_confirm"


class ResolveStatus(str, Enum):
    """澄清解析状态（内部管线，非 IntentResponse.action）。"""

    RESOLVED = "resolved"
    ASK_AGAIN = "ask_again"
    REJECT = "reject"
    OFF_TOPIC = "off_topic"


class ResolveOp(str, Enum):
    """
    澄清解析操作（内部管线）。

    注意：这些值不得作为成功落叶子时的 IntentResponse.action；
    对外 action 始终使用 IntentAction（来自 pending.action）。
    """

    CONFIRM = "confirm"
    SELECT = "select"
    CORRECT = "correct"
    REJECT = "reject"
    ASK_AGAIN = "ask_again"
    NEW_INTENT = "new_intent"


class EventType(str, Enum):
    """事件数量/时间类型（新事件场景）。"""

    NUMBER = "number"
    TIME = "time"
    ONE = "one"


# 标准喂养动作变体（写入向量 metadata / id 用）
STANDARD_INTENT_ACTIONS: tuple[IntentAction, ...] = (
    IntentAction.START,
    IntentAction.END,
    IntentAction.ONE,
)

VALID_RESOLVE_OPS: frozenset[str] = frozenset(op.value for op in ResolveOp)
