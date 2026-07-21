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
    - data_requirement: 数据需求判断结果（event_ids, time_range, limit）
    - history_events: 历史记录列表
    - knowledge: 向量检索结果列表
    - baby_profile: 宝宝画像信息
    """

    # 输入字段（路由传入）
    question: str                      # 用户的诊疗问题
    device_no: str                     # 设备编号
    model_config: Dict[str, Any]       # 模型配置

    # 中间字段（各节点填充）
    data_requirement: Dict[str, Any]        # 数据需求判断结果
    history_events: List[Dict[str, Any]]    # 历史记录列表
    knowledge: List[Dict[str, Any]]         # 向量检索结果
    baby_profile: Dict[str, Any]            # 宝宝画像
