"""
意图分类节点

业务说明：
使用 LLM 对用户输入进行意图分类，识别增删改查。
提示词注入全量树（父+叶子）；记事件仍落到叶子，查记录可输出父 id。
意图缓存未命中后的唯一语义入口（不再经事件名向量）。

设计思路：
1. 构建包含事件字典的系统提示词
2. 调用 LLM 进行意图分类
3. 解析 LLM 返回的结构化 JSON 结果
4. 字典外名称不当新事件类型；查记录可当备注
5. 分类路径默认先确认，免确认只留给意图缓存命中
"""

import json
import logging
from typing import Any, Dict

from app.feeding.graphs.nodes.prompts.intent_classification import (
    build_intent_classification_system_prompt,
    build_intent_classification_user_message,
)
from app.feeding.schemas.intent_result import IntentResult, coerce_intent_result
from app.feeding.services.event_name_match import match_feeding_event
from app.feeding.utils.quantity_extractor import extract_quantity_from_text
from app.shared.constants import (
    IntentAction,
    LLM_OVERLOAD_RETRY_MESSAGE,
    MatchSource,
    TargetType,
)
from app.shared.graphs.node_thinking import emit_thinking
from app.shared.graphs.state_patch import state_get
from app.shared.llm_client import llm_client, llm_model_config_from_mapping

# 初始化日志记录器
logger = logging.getLogger(__name__)


def _parse_intent_result(content: str) -> Dict[str, Any]:
    """
    解析 LLM 返回的意图结果

    业务逻辑：
    1. 清理 LLM 返回的内容（去除 markdown 代码块标记）
    2. 解析 JSON 格式的意图结果
    3. 处理解析错误，返回默认的 conversation 类型意图

    Args:
        content: LLM 返回的原始文本内容

    Returns:
        解析后的意图结果字典
    """
    try:
        # 清理 markdown 代码块标记
        cleaned = content.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        result = json.loads(cleaned)
        logger.info(f"LLM 意图解析成功: {json.dumps(result, ensure_ascii=False)}")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"LLM 返回内容 JSON 解析失败: {e}, content={content[:200]}")
        # 返回默认的 conversation 类型
        return {
            "target_type": TargetType.CONVERSATION.value,
            "action": IntentAction.REPLY.value,
            "event_name": "",
            "event_id": "",
            "keywords": [],
            "content": content,
        }


async def classify_intent(state: Any) -> Dict[str, Any]:
    """
    意图分类节点

    业务逻辑：
    1. 从状态中获取用户输入和事件字典
    2. 构建系统提示词和用户消息
    3. 调用 LLM 进行意图分类
    4. 解析 LLM 返回的结构化 JSON 结果
    5. 忽略 LLM 返回的 event_type，计时与否以事件字典为准
    6. 优先使用向量匹配已提取的数量，未提取到时尝试本地提取作为 fallback
    7. 根据匹配情况设置 need_confirm 标志

    Args:
        state: 当前图状态，包含用户输入文本、事件字典等信息

    Returns:
        更新后的状态字典，包含意图分类结果
    """
    # 业务说明：路由注入 user_input / llm_model，与 IntentState 对齐；兼容旧字段 text / model
    text = state_get(state, "user_input") or state_get(state, "text", "")
    # 分类必须看见父名；叶子视图不够匹配「换尿布」
    event_dictionary = (
        state_get(state, "event_dictionary_full")
        or state_get(state, "event_dictionary")
        or []
    )
    device_no = state_get(state, "device_no", "")

    # llm_model 为图 State 字段；兼容过渡 dict 键 model_config / model；缺模由 llm_client 抛错
    llm_model = (
        state_get(state, "llm_model")
        or state_get(state, "model_config")
        or state_get(state, "model")
        or {}
    )
    llm_model_config = llm_model_config_from_mapping(llm_model)

    logger.info(
        "开始意图分类: device_no=%s, text=%s..., model=%s/%s",
        device_no,
        text[:20],
        (llm_model_config.provider if llm_model_config else "(missing)"),
        (llm_model_config.name if llm_model_config else "-"),
    )

    try:
        # 构建提示词：字段含义 + 表 + 进行中数据；备注反查在分类后做
        system_prompt = build_intent_classification_system_prompt(
            event_dictionary,
            in_progress_hint=str(state_get(state, "in_progress_hint") or ""),
        )
        user_message = build_intent_classification_user_message(text)

        response = await llm_client.invoke(
            messages=[{"role": "user", "content": user_message}],
            model_config=llm_model_config,
            system_prompt=system_prompt,
        )


        # 解析意图结果
        intent_result = _parse_intent_result(response.content)

        # 字典匹配（含简称/进行态）；对不上留给分类后备注反查，不当新类型
        if intent_result.get("event_name") and not intent_result.get("event_id"):
            matched_event = match_feeding_event(
                intent_result["event_name"], event_dictionary
            )
            if matched_event:
                intent_result["event_id"] = matched_event["event_id"]
                intent_result["event_name"] = matched_event.get("event_name") or intent_result[
                    "event_name"
                ]
                intent_result["is_new_event"] = False
            else:
                # 禁止新建：清空 id，名称留给备注反查；暂不写入 missing
                intent_result["is_new_event"] = False
                intent_result["event_id"] = ""
        elif intent_result.get("event_id"):
            intent_result["is_new_event"] = False

        # 数量提取：优先使用向量匹配已提取的数量，未提取到时尝试本地提取
        vector_quantity = None
        prior_ir = coerce_intent_result(state_get(state, "intent_result"))
        if prior_ir.quantity is not None:
            vector_quantity = prior_ir.quantity

        if vector_quantity is not None:
            intent_result["quantity"] = vector_quantity
            logger.info(f"使用向量匹配提取的数量: quantity={vector_quantity}")
        elif intent_result.get("quantity") is None:
            # 向量匹配未提取到数量，尝试本地提取
            extracted_quantity = extract_quantity_from_text(text)
            if extracted_quantity is not None:
                intent_result["quantity"] = extracted_quantity
                logger.info(f"本地提取数量成功: quantity={extracted_quantity}")

        # 确保所有字段都有默认值
        # 业务说明：feeding 结果由路由层做叶子校验 / 父消歧 / 自由文本软确认
        intent_result.setdefault("target_type", TargetType.CONVERSATION.value)
        intent_result.setdefault("action", IntentAction.REPLY.value)
        intent_result.setdefault("event_name", "")
        intent_result.setdefault("event_id", "")
        intent_result.setdefault("quantity", None)
        # 类型以字典为准，不采信模型返回的 event_type
        intent_result["event_type"] = None
        intent_result.setdefault("event_unit", None)
        intent_result.setdefault("is_new_event", False)
        intent_result.setdefault("op", "")
        intent_result.setdefault("remark_keyword", state_get(state, "remark_keyword") or "")
        intent_result.setdefault("event_ids", [])
        intent_result.setdefault("missing_events", [])
        intent_result.setdefault("match_source", MatchSource.LLM.value)
        intent_result.setdefault("match_confidence", 1.0)
        intent_result.setdefault("keywords", [])
        intent_result.setdefault("content", "")
        intent_result.setdefault("events", [])

        # 多事件场景处理
        if intent_result.get("events"):
            # 为多事件中的每个事件匹配 event_id；去掉模型误填的类型
            for event in intent_result["events"]:
                if not isinstance(event, dict):
                    continue
                # 去掉模型误填的类型，落库只认字典
                event.pop("event_type", None)
                if event.get("event_name") and not event.get("event_id"):
                    matched = match_feeding_event(event["event_name"], event_dictionary)
                    if matched:
                        event["event_id"] = matched["event_id"]
                        event["event_name"] = matched.get("event_name") or event[
                            "event_name"
                        ]
                    else:
                        event["event_id"] = ""
                # 多事件中每个事件也尝试提取数量
                if event.get("quantity") is None:
                    event_quantity = extract_quantity_from_text(text)
                    if event_quantity is not None:
                        event["quantity"] = event_quantity
            # 复合切换漏标 multi 时，按子项数量补上，确认话术才能带动作
            if (
                len(intent_result["events"]) > 1
                and intent_result.get("action") != IntentAction.MULTI.value
            ):
                intent_result["action"] = IntentAction.MULTI.value

        # 分类默认先确认；闲聊/退出不确认
        op = (intent_result.get("op") or "").strip().lower()
        if not op:
            if intent_result.get("target_type") == TargetType.HISTORY.value:
                op = "read"
            elif intent_result.get("action") == IntentAction.SEARCH.value:
                op = "read"
            elif intent_result.get("target_type") == TargetType.FEEDING.value:
                op = "create"
        intent_result["op"] = op
        if op == "read":
            intent_result["target_type"] = TargetType.HISTORY.value
            intent_result["action"] = IntentAction.SEARCH.value
            # 点查至少要有 event_ids，便于确认后拉史与父展开
            eid = str(intent_result.get("event_id") or "")
            ids = [str(x) for x in (intent_result.get("event_ids") or []) if x not in (None, "")]
            if eid and eid not in ids:
                ids = [eid] + ids
            intent_result["event_ids"] = ids
        # 分类一律先确认；闲聊/退出除外。免确认只留给意图缓存命中。
        target = intent_result.get("target_type")
        is_crud = op in ("create", "read", "update", "delete") or target in (
            TargetType.FEEDING.value,
            TargetType.HISTORY.value,
        )
        if is_crud or intent_result.get("action") == IntentAction.MULTI.value:
            need_confirm = True
        elif target in (TargetType.CONVERSATION.value, TargetType.EXIT.value):
            need_confirm = False
        else:
            need_confirm = True

        logger.info(
            f"意图分类完成: op={op}, target_type={intent_result['target_type']}, "
            f"action={intent_result['action']}, "
            f"event_name={intent_result['event_name']}, "
            f"event_id={intent_result['event_id']}, "
            f"need_confirm={need_confirm}"
        )

        return {
            "intent_result": IntentResult.model_validate(intent_result),
            "match_confidence": 1.0,
            "match_source": MatchSource.LLM.value,
            "need_confirm": need_confirm,
            "confirm_message": intent_result.get("confirm_message") or "",
        }

    except Exception as e:
        logger.error(f"意图分类失败: {e}", exc_info=True)
        # 失败不换模：推 thinking（有 writer 时）并软回脑电波文案
        emit_thinking("classify_intent", LLM_OVERLOAD_RETRY_MESSAGE)
        return {
            "intent_result": IntentResult(
                target_type=TargetType.CONVERSATION.value,
                action=IntentAction.REPLY.value,
                event_name="",
                event_id="",
                quantity=None,
                event_type=None,
                event_unit=None,
                is_new_event=False,
                match_source=MatchSource.LLM.value,
                match_confidence=0.0,
                keywords=[],
                content=LLM_OVERLOAD_RETRY_MESSAGE,
            ),
            "match_confidence": 0.0,
            "match_source": MatchSource.LLM.value,
        }
