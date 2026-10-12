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


class IntentOp(str, Enum):
    """意图 CRUD 轴（IntentResponse.op）。"""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"


class TargetType(str, Enum):
    """
    意图轨（IntentResponse.target_type）。

    业务说明：
    权威新轨：create|read|update|delete|exit|other（C/R/U/D）。
    查史与预测均落在 read，由 read_source 等子维区分。
    feeding/history/predict/conversation/suggest 为遗留值，读写时须 normalize。
    """

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXIT = "exit"
    OTHER = "other"
    # --- 遗留（兼容旧飞轮/在途状态；新写入应 normalize 到上列）---
    FEEDING = "feeding"
    HISTORY = "history"
    PREDICT = "predict"
    CONVERSATION = "conversation"
    SUGGEST = "suggest"


# 权威六轨（新写入 / OP 飞轮）
TARGET_TYPE_RAILS = frozenset(
    {
        TargetType.CREATE.value,
        TargetType.READ.value,
        TargetType.UPDATE.value,
        TargetType.DELETE.value,
        TargetType.EXIT.value,
        TargetType.OTHER.value,
    }
)


def normalize_target_rail(raw: str) -> str:
    """
    将任意 target_type 规范为六轨之一。

    predict/history → read（预测须另带 read_source=predict）；
    feeding → create；conversation/suggest → other。
    """
    s = (raw or "").strip().lower()
    if s in TARGET_TYPE_RAILS:
        return s
    legacy = {
        TargetType.FEEDING.value: TargetType.CREATE.value,
        TargetType.HISTORY.value: TargetType.READ.value,
        TargetType.PREDICT.value: TargetType.READ.value,
        TargetType.CONVERSATION.value: TargetType.OTHER.value,
        TargetType.SUGGEST.value: TargetType.OTHER.value,
    }
    return legacy.get(s, TargetType.OTHER.value)


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

# LLM 调用失败时对用户可见的固定文案（不换模，请稍后重试）
LLM_OVERLOAD_RETRY_MESSAGE = "脑电波过载，请稍后重试"
