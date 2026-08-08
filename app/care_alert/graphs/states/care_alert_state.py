"""
护理留意图状态

业务说明：
复用 tip/clinic 共享节点字段（history_events / knowledge / baby_profile），
并增加 day、预置上下文与最终 items 输出。
"""

from typing import Any, Dict, List, Optional, TypedDict


class CareAlertState(TypedDict, total=False):
    """
    护理留意图状态

    字段说明：
    - device_no / day / model_config：路由注入
    - question：供 search_vectors 检索用查询词
    - data_requirement：驱动 fetch_history（近 7 天）
    - baby_age_months：请求透传或 derive_baby_age 写入
    - history_events / knowledge / baby_profile：数据准备结果
    - items：generate_care_alerts 产出的 DTO 列表（dict）
    """

    device_no: str
    day: str
    model_config: Dict[str, Any]
    question: str
    data_requirement: Dict[str, Any]
    baby_age_months: Optional[int]
    history_events: List[Dict[str, Any]]
    knowledge: List[Dict[str, Any]]
    baby_profile: Dict[str, Any]
    # 可选：Go 透传的原始上下文（提示词可引用）
    history_summary: Any
    kg_context: Any
    items: List[Dict[str, Any]]
