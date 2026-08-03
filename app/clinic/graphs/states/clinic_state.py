"""
诊疗图的状态定义

业务说明：
定义 clinic_graph 的 State 结构，包含诊疗流程中所有节点需要的输入和输出字段。
State 在图中传递，每个节点读取需要的字段并返回需要更新的字段。

设计思路：
1. 使用 TypedDict 定义状态，符合 LangGraph 的标准做法
2. 与 IntentState 分离，避免无关字段干扰
3. 字段命名使用蛇形命名，与 Python 代码风格一致
"""

from typing import Any, Dict, List, TypedDict


class ClinicState(TypedDict, total=False):
    """
    诊疗图的状态类

    业务说明：
    存储 clinic_graph 执行过程中的所有状态数据。
    每个节点读取需要的字段，返回需要更新的字段（字典格式）。

    字段说明：
    - question: 用户的诊疗问题
    - device_no: 设备编号
    - model_config: 模型配置（provider, name, max_in_flight）
    - event_dictionary: 事件字典列表（路由注入；须声明否则 LangGraph 静默丢弃）
    - needs_history: 门禁结果，是否需要喂养历史
    - force_needs_history: 上游强制需要历史（如 intent history）
    - data_requirement: 数据需求判断结果（event_ids, time_range, limit）
    - history_events: 历史记录列表
    - knowledge: 向量检索结果列表
    - baby_profile: 宝宝画像信息
    """

    # 输入字段（路由传入）
    question: str                      # 家长本轮问题
    device_no: str                     # 设备编号
    model_config: Dict[str, Any]       # 模型配置
    event_dictionary: List[Dict[str, Any]]  # 事件字典列表（供 judge_data_requirement）
    # tip/clinic 共享陪伴对话（须声明否则 LangGraph 静默丢弃）
    chat_context: str
    # True 时跳过 search_vectors（intent history 纯查记录）
    skip_knowledge: bool
    # True 时门禁跳过 LLM，必须拉历史（intent history）
    force_needs_history: bool

    # 中间字段（各节点填充）
    needs_history: bool                     # 是否需要喂养历史（门禁）
    data_requirement: Dict[str, Any]        # 数据需求判断结果
    history_events: List[Dict[str, Any]]    # 历史记录列表
    knowledge: List[Dict[str, Any]]         # 向量检索结果
    baby_profile: Dict[str, Any]            # 宝宝画像
