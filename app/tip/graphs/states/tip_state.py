"""
小贴士图的状态定义

业务说明：
定义 tip_graph 的 State 结构，包含小贴士生成流程中所有节点需要的输入和输出字段。
State 在图中传递，每个节点读取需要的字段并返回需要更新的字段。

设计思路：
1. 使用 TypedDict 定义状态，符合 LangGraph 的标准做法
2. 与 ClinicState 分离：小贴士有 event_info；月龄由 derive_baby_age 自算（可选）
3. current_time 不再由请求驱动，写提示词时由 Python 用 Asia/Shanghai 生成
4. 复用共享节点需要的数据字段保持一致
"""

from typing import Any, Dict, List, Optional, TypedDict


class TipState(TypedDict, total=False):
    """
    小贴士图的状态类

    业务说明：
    存储 tip_graph 执行过程中的所有状态数据。
    每个节点读取需要的字段，返回需要更新的字段（字典格式）。

    字段说明：
    - event_info: 触发小贴士的事件信息（event_id, event_name）
    - device_no: 设备编号
    - model_config: 模型配置（provider, name, max_in_flight）
    - baby_age_months: 自算月龄；未知时为 None（不得用 0 表示未知）
    - data_requirement: 数据需求判断结果（event_ids, time_range, limit）
    - history_events: 历史记录列表
    - knowledge: 向量检索结果列表
    - baby_profile: 宝宝画像信息
    - response: 最终生成的小贴士内容（流式模式下由路由层累积）
    """

    # 输入字段（路由传入）
    event_info: Dict[str, Any]          # 触发事件信息，包含 event_id 和 event_name
    device_no: str                      # 设备编号
    model_config: Dict[str, Any]        # 模型配置

    # 派生字段（derive_baby_age 写入；未知为 None）
    baby_age_months: Optional[int]      # 宝宝月龄；None=未知，0=算出的 0 个月

    # 中间字段（各节点填充）
    data_requirement: Dict[str, Any]        # 数据需求判断结果
    history_events: List[Dict[str, Any]]    # 历史记录列表
    knowledge: List[Dict[str, Any]]         # 向量检索结果
    baby_profile: Dict[str, Any]            # 宝宝画像

    # 输出字段（流式生成节点填充）
    response: str                           # 最终小贴士内容
