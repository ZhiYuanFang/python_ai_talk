"""
调用诊疗 Agent 节点

业务说明：
LangGraph 节点：当意图被识别为 conversation（对话）或 suggest（建议）时，
在意图图内部直接调用 clinic_graph 获取回答，避免前端发起第二次 HTTP 请求。
clinic_graph 是同一进程内的 LangGraph 实例，通过 ainvoke 直接调用，不走 HTTP。

clinic_graph 本身只负责数据准备（判断数据需求→拉取历史→向量检索→获取宝宝画像），
不包含 LLM 回答生成节点。因此本节点需要在 clinic_graph 执行完成后，
复用 clinic 模块的 generate_response 节点生成最终回答。

失败时返回兜底文案，保证意图始终返回有效响应。

设计思路：
1. 从 IntentState 中提取 user_input、device_no、model_config、intent_result
2. 构造 ClinicState 兼容的初始状态（question/device_no/model_config）
3. 调用 clinic_graph.ainvoke 异步执行诊疗图，完成数据准备
4. 将 clinic 返回的数据准备结果与意图状态合并（补充 user_input、intent_result）
5. 调用 generate_response 节点，基于完整上下文生成 LLM 回答
6. 成功时填充 intent_result（conversation/reply/clinic 回答）
7. 失败时兜底文案，保证前端能拿到统一结构的响应

使用场景：
- 意图为 conversation：用户闲聊式问题，需调用 clinic 拿到带上下文的回答
- 意图为 suggest：用户需要成长建议，需走完 clinic 的完整链路
- 前端不希望发起第二次 HTTP 请求，由意图图内部直接获取答案
"""

# 日志模块导入
import logging
# 类型提示导入
from typing import Any, Dict

# 诊疗图实例导入（同进程内调用，仅做数据准备）
from app.clinic.graphs.clinic_graph import clinic_graph
# 诊疗回答生成节点导入（复用 clinic 模块的 LLM 回答生成逻辑）
from app.clinic.graphs.nodes.generate_response import generate_response

# 初始化日志记录器
logger = logging.getLogger(__name__)

# 诊疗调用失败时的兜底文案
# 业务说明：clinic_graph 调用异常或返回为空时，使用该文案保证响应不为空
CLINIC_FALLBACK = "抱歉，我暂时无法回答您的问题，请稍后再试。"


async def call_clinic_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    调用诊疗 Agent 节点函数

    业务逻辑：
    1. 从意图状态中读取 user_input、device_no、model_config、intent_result
    2. 构造 ClinicState 兼容的初始状态（字段映射：user_input → question）
    3. 通过 ainvoke 同进程异步调用 clinic_graph 完成数据准备（历史/知识/宝宝画像）
    4. 将 clinic 返回的数据准备结果合并到意图状态中，补充 user_input 和 intent_result
    5. 调用 generate_response 节点，基于完整上下文生成 LLM 回答
    6. 从 generate_response 返回中提取 response 字段作为回答内容
    7. 成功时填充 intent_result（conversation/reply/clinic 回答）
    8. 失败时填充兜底文案，保证 intent_result 结构完整
    9. 全程记录调用日志和结果日志，便于排查问题

    Args:
        state: 当前意图图状态，包含 user_input、device_no、model_config、intent_result 等字段

    Returns:
        需要更新的 State 字段字典，包含 intent_result（target_type/action/content）

    Side Effects:
        - 同进程内异步调用 clinic_graph，可能产生向量检索、数据库查询等副作用
        - 调用 generate_response 会产生 LLM 调用副作用
        - 失败时会记录 error 日志，但不抛出异常，保证意图图流程不中断
    """
    # 从意图状态中提取用户输入文本
    user_input = state.get("user_input", "")
    # 从意图状态中提取设备编号
    device_no = state.get("device_no", "")
    # 从意图状态中提取模型配置
    model_config = state.get("model_config", {})
    # 从意图状态中提取意图分类结果（用于判断 suggest/history 选择对应提示词）
    intent_result = state.get("intent_result", {})

    # 记录调用日志：标记开始调用诊疗 Agent
    logger.info(
        f"开始调用诊疗 Agent，device_no={device_no}, user_input={user_input[:50]}"
    )

    # 构造 ClinicState 兼容的初始状态
    # 业务说明：clinic_graph 的入口字段是 question，需将 user_input 映射过去
    clinic_state = {
        # 用户的诊疗问题（由意图图的 user_input 映射而来）
        "question": user_input,
        # 设备编号，透传用于历史拉取和宝宝画像查询
        "device_no": device_no,
        # 模型配置，透传给 clinic 内部的 LLM 调用
        "model_config": model_config,
    }

    try:
        # 第一步：同进程异步调用诊疗图，完成数据准备
        # 业务说明：clinic_graph 执行 judge→fetch_history→search_vectors→fetch_baby_profile
        # 返回状态中包含 history_events、knowledge、baby_profile 等数据
        clinic_result = await clinic_graph.ainvoke(clinic_state)

        # 第二步：将 clinic 数据准备结果与意图状态合并，构造 generate_response 所需的完整状态
        # 业务说明：generate_response 需要 user_input、intent_result、history_events、knowledge、baby_profile、model_config
        # clinic_result 中缺少 user_input 和 intent_result，需要从原意图状态补充
        merged_state: Dict[str, Any] = dict(clinic_result)
        # 补充用户输入文本（generate_response 读取 user_input 字段构建用户消息）
        merged_state["user_input"] = user_input
        # 补充意图分类结果（generate_response 根据 intent_result.target_type 选择提示词）
        # 业务说明：suggest 意图使用建议提示词，其他意图（含 conversation）使用历史回答提示词
        merged_state["intent_result"] = intent_result

        # 第三步：调用 generate_response 节点生成 LLM 回答
        # 业务说明：generate_response 是 async 函数，接收状态字典，返回 {"response": "..."}
        generate_result = await generate_response(merged_state)
        # 从返回结果中提取 response 字段作为回答内容
        clinic_response = generate_result.get("response", "")

        # 如果回答为空，使用兜底文案保证响应非空
        if not clinic_response:
            # 记录警告日志：generate_response 返回为空
            logger.warning("诊疗 Agent 的 generate_response 返回为空，使用兜底文案")
            # 兜底文案
            clinic_response = CLINIC_FALLBACK

        # 记录成功日志：诊疗 Agent 调用完成
        logger.info(
            f"诊疗 Agent 调用成功，response={clinic_response[:50]}"
        )

        # 成功时填充 intent_result：conversation 类型、reply 动作、clinic 回答
        return {
            "intent_result": {
                # 目标类型为对话（conversation/suggest 都归为对话回复）
                "target_type": "conversation",
                # 动作为直接回复
                "action": "reply",
                # 回复内容：诊疗 Agent 生成的回答
                "content": clinic_response,
            }
        }

    except Exception as e:
        # 记录错误日志：诊疗 Agent 调用失败，包含异常信息
        logger.error(f"诊疗 Agent 调用失败: {str(e)}", exc_info=True)

        # 失败时填充 intent_result：conversation 类型、reply 动作、兜底文案
        # 业务说明：即使调用失败也返回结构化响应，避免前端拿到空数据
        return {
            "intent_result": {
                # 目标类型为对话
                "target_type": "conversation",
                # 动作为直接回复
                "action": "reply",
                # 回复内容：兜底文案
                "content": CLINIC_FALLBACK,
            }
        }
