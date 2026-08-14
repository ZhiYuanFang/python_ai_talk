"""
跨图共享节点 Protocol

业务说明：
shared 节点只依赖所需字段，不导入业务模块完整 State。
运行时用 state_get 读取，Protocol 供类型标注文档化。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from app.shared.schemas.data_requirement import DataRequirement


@runtime_checkable
class HasDeviceNo(Protocol):
    device_no: str


@runtime_checkable
class HasEventDictionary(Protocol):
    event_dictionary: List[Dict[str, Any]]


@runtime_checkable
class HasDataRequirement(Protocol):
    data_requirement: Optional[DataRequirement]


@runtime_checkable
class HasLlmModel(Protocol):
    """图内 LLM 配置（原 model_config 通道，现名 llm_model）。"""

    llm_model: Dict[str, Any]


@runtime_checkable
class HasHistoryEvents(Protocol):
    history_events: List[Dict[str, Any]]


@runtime_checkable
class HasBabyProfile(Protocol):
    baby_profile: Dict[str, Any]
