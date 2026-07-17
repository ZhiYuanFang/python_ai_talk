"""
意图分析图的状态定义

业务说明：
定义 intent_graph 的 State 结构，包含意图分析流程中所有节点需要的输入和输出字段。
State 在图中传递，每个节点读取需要的字段并返回需要更新的字段。

设计思路：
1. 使用 TypedDict 定义状态，符合 LangGraph 的标准做法
2. 所有字段均为可选（TypedDict 默认 total=True，但所有字段初始可能为空）
3. 字段命名使用蛇形命名，与 Python 代码风格一致
"""

from typing import Any, Dict, List, Optional, TypedDict


class IntentState(TypedDict, total=False):
    """
    意图分析图的状态类

    业务说明：
    存储 intent_graph 执行过程中的所有状态数据。
    每个节点读取需要的字段，返回需要更新的字段（字典格式）。

    字段说明：
    - user_input: 用户输入的自然语言文本
    - device_no: 设备编号
    - model_config: 模型配置（provider, name, max_in_flight）
    - event_dictionary: 事件字典列表
    - intent_result: 意图分类结果（target_type, action, event_name, keywords, content）
    - data_requirement: 数据需求判断结果（event_ids, time_range, limit）
    - history_events: 历史记录列表
    - knowledge: 向量检索结果列表
    - baby_profile: 宝宝画像信息
    - response: LLM 生成的最终回答
    """

    # 输入字段（路由传入）
    user_input: str                    # 用户输入的自然语言文本
    device_no: str                     # 设备编号
    model_config: Dict[str, Any]       # 模型配置

    # 中间字段（各节点填充）
    event_dictionary: List[Dict[str, Any]]  # 事件字典列表
    intent_result: Dict[str, Any]           # 意图分类结果
    data_requirement: Dict[str, Any]        # 数据需求判断结果
    history_events: List[Dict[str, Any]]    # 历史记录列表
    knowledge: List[Dict[str, Any]]         # 向量检索结果
    baby_profile: Dict[str, Any]            # 宝宝画像

    # 输出字段（最终结果）
    response: str                      # LLM 生成的回答
