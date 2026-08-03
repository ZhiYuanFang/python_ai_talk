"""
诊疗图的状态定义

业务说明：
定义 clinic_graph 的 State 结构，包含诊疗流程中所有节点需要的输入和输出字段。
State 在图中传递，每个节点读取需要的字段并返回需要更新的字段。
"""

from typing import Any, Dict, List, Optional, TypedDict


class ClinicState(TypedDict, total=False):
    """clinic_graph 执行过程中的状态数据。"""

    # 输入字段（路由传入）
    question: str
    device_no: str
    model_config: Dict[str, Any]
    event_dictionary: List[Dict[str, Any]]
    chat_context: str
    skip_knowledge: bool
    force_needs_history: bool
    block_fast_path: bool

    # 中间字段
    needs_history: bool
    data_requirement: Dict[str, Any]
    history_events: List[Dict[str, Any]]
    knowledge: List[Dict[str, Any]]
    baby_profile: Dict[str, Any]
    baby_age_months: Optional[int]
    age_band: Optional[str]
    standalone_question: Optional[str]
    qa_rewrite_miss_reason: str
    qa_hit: bool
    qa_answer: str
    qa_miss_reason: str
    qa_match_id: str
    qa_match_score: float
