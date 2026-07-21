"""
确认准备节点

业务说明：
LangGraph 节点：根据意图分类结果生成确认消息，请用户确认操作意图。
当意图分类识别为喂养场景后，需要向用户展示拟执行的操作，避免误操作。

设计思路：
1. 从 State 中读取 intent_result，提取事件名和动作类型
2. 将动作类型映射为用户友好的中文描述
3. 拼接确认消息，引导用户回复「确认」或「取消」
4. 生成 conversation_id（会话 ID，用于恢复中断的图执行）
5. 调用 LangGraph 的 interrupt() 函数中断图执行，等待用户确认
6. interrupt 恢复后（用户通过 confirm 接口恢复），将用户反馈写入 State
7. 返回 need_confirm、confirm_message、conversation_id、user_feedback 更新 State

使用场景：
- 喂养场景意图确认：用户输入被识别为喂养意图后，生成确认消息
- 防止误操作：在执行记录前让用户确认，提升交互安全性
- 中断恢复：用户通过 confirm 接口恢复图执行，传入 confirm/reject 反馈
"""

# 类型提示导入
from typing import Any, Dict

# LangGraph interrupt 函数导入，用于中断图执行等待用户确认
from langgraph.types import interrupt


# 动作类型到中文描述的映射字典
ACTION_DESC_MAP = {
    "start": "开始记录",  # 开始记录动作
    "end": "结束记录",  # 结束记录动作
    "one": "记录一次",  # 记录一次动作
}


def _build_multi_event_confirm_message(events: list) -> str:
    """
    构建多事件确认消息

    业务逻辑：
    根据事件列表生成确认消息，支持 2 个以内事件的详细描述和超过 2 个事件的简化描述。

    Args:
        events: 事件列表，每个元素包含 action 和 event_name

    Returns:
        确认消息字符串
    """
    if not events:
        return "您确认要记录这些事件吗？请回复「确认」或「取消」。"

    # 2 个以内事件：详细描述每个事件
    if len(events) <= 2:
        event_descs = []
        for event in events:
            action = event.get("action", "one")
            event_name = event.get("event_name", "")
            action_desc = ACTION_DESC_MAP.get(action, "记录一次")
            event_descs.append(f"{action_desc}「{event_name}」")

        if len(event_descs) == 1:
            return f"您是要{event_descs[0]}吗？请回复「确认」或「取消」。"
        else:
            return f"您是要：{event_descs[0]}，{event_descs[1]}吗？请回复「确认」或「取消」。"

    # 超过 2 个事件：简化描述
    else:
        return f"您确认要记录这{len(events)}个事件吗？请回复「确认」或「取消」。"


async def prepare_confirm(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    确认准备节点函数

    业务逻辑：
    1. 从 State 中读取意图分类结果
    2. 提取事件名称和动作类型（支持多事件）
    3. 将动作类型映射为中文描述
    4. 生成确认消息，引导用户确认或取消（支持多事件批量确认）
    5. 生成 conversation_id（会话 ID，用于恢复中断的图执行）
    6. 调用 interrupt() 中断图执行，将确认信息传递给调用方
    7. interrupt 恢复后，将用户反馈（confirm/reject）写入 State
    8. 返回确认标记、确认消息、会话 ID、用户反馈更新 State

    interrupt 机制说明：
    - interrupt(value) 调用后，图执行立即暂停，状态保存到 MemorySaver 检查点
    - interrupt 的参数 value 会通过 ainvoke 的返回值暴露给调用方
    - 调用方（路由层）从中断状态提取确认信息，返回给客户端
    - 客户端调用 confirm 接口时，路由层用 Command(resume=user_feedback) 恢复图执行
    - interrupt() 函数返回 Command(resume=...) 中传入的值（即用户反馈）
    - 节点继续执行 interrupt 之后的代码

    Args:
        state: 当前图状态，包含 intent_result 字段

    Returns:
        需要更新的 State 字段字典，包含 need_confirm、confirm_message、
        conversation_id 和 user_feedback

    Side Effects:
        - 调用 interrupt() 会暂停图执行，状态保存到 MemorySaver 检查点
        - 恢复后 user_feedback 被写入 State，供 handle_feedback 节点使用
    """
    # 从 State 中获取意图分类结果
    intent_result = state.get("intent_result", {})

    # 从意图结果中获取动作类型，默认为 "one"
    action = intent_result.get("action", "one")

    # 判断是否为多事件场景
    if action == "multi":
        # 多事件场景：构建包含所有事件的确认消息
        events = intent_result.get("events", [])
        confirm_message = _build_multi_event_confirm_message(events)
    else:
        # 单事件场景：提取事件名称
        event_name = intent_result.get("event_name", "")
        # 根据动作类型映射获取中文描述，未知动作默认使用 "记录一次"
        action_desc = ACTION_DESC_MAP.get(action, "记录一次")
        # 生成确认消息，引导用户回复确认或取消
        confirm_message = f"您是要{action_desc}「{event_name}」吗？请回复「确认」或「取消」。"

    # 从 State 中获取 conversation_id（由路由层生成并注入 State）
    # 业务说明：conversation_id 等同于 LangGraph 的 thread_id，
    # 路由层在调用 ainvoke 前生成 thread_id 并注入 initial_state
    # 客户端调用 confirm 接口时传入此 ID，路由层用它恢复 MemorySaver 检查点
    conversation_id = state.get("conversation_id", "")

    # 调用 interrupt() 中断图执行，将确认信息传递给调用方
    # 业务说明：
    # - interrupt 调用后图执行立即暂停，状态保存到 MemorySaver[conversation_id]
    # - interrupt 的参数会通过 ainvoke 返回值的 __interrupt__ 字段暴露给调用方
    # - 调用方（路由层）从中提取 need_confirm、confirm_message、conversation_id
    # - 客户端调用 confirm 接口时，路由层用 Command(resume=user_feedback) 恢复
    # - interrupt() 返回 Command(resume=...) 中传入的值（即用户反馈字符串）
    user_feedback = interrupt({
        "need_confirm": True,
        "confirm_message": confirm_message,
        "conversation_id": conversation_id,
    })

    # interrupt 恢复后，user_feedback 是用户通过 confirm 接口传入的反馈
    # 业务说明：user_feedback 的值为 "confirm"（确认）或 "reject"（否定）
    # 将 user_feedback 写入 State，供 handle_feedback 节点读取并执行相应逻辑
    return {
        "need_confirm": True,
        "confirm_message": confirm_message,
        "conversation_id": conversation_id,
        "user_feedback": user_feedback,
    }
