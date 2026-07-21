"""
意图分类提示词构建模块

业务说明：
构建意图分类节点使用的系统提示词和用户消息。
根据事件字典，引导 LLM 正确识别用户输入的意图类型和动作。

设计思路：
1. 将事件字典格式化后注入提示词
2. 明确列出所有意图类型和动作类型
3. 要求 LLM 返回严格的 JSON 格式
4. 提供示例帮助 LLM 理解格式
"""

import json
from typing import Any, Dict, List


def build_intent_classification_system_prompt(event_dictionary: List[Dict[str, Any]]) -> str:
    """
    构建意图分类的系统提示词

    业务逻辑：
    将事件字典格式化为系统提示词，引导 LLM 正确识别意图。
    包含意图类型说明、动作类型说明、返回格式要求和注意事项。

    Args:
        event_dictionary: 事件字典列表，每个元素包含 event_id, event_name, keywords 等字段

    Returns:
        系统提示词字符串
    """
    # 将事件字典转换为字符串格式，仅保留 id 和 name 以简化展示
    events_simple = [
        {"id": e.get("event_id", e.get("id", "")), "name": e.get("event_name", "")}
        for e in event_dictionary
    ]
    event_str = json.dumps(events_simple, ensure_ascii=False, indent=2)

    # 构建系统提示词
    return f"""
你是一个专业的母婴喂养意图分析助手。
请分析用户输入的自然语言文本，识别其意图，并返回结构化的 JSON 结果。

可用的事件类型如下（id 为事件的唯一标识，name 为事件名称）：
{event_str}

意图类型说明：
- feeding: 喂养记录相关意图
  - start: 开始喂养记录（如"开始喂奶"、"开始喂奶粉"）
  - end: 结束喂养记录（如"结束喂奶"、"停止喂奶粉"）
  - one: 单次喂养记录（如"刚才喝了120ml奶粉"）
  - multi: 多个喂养记录（如"没吃，睡着了"包含结束喂养和开始睡眠）
- history: 历史查询相关意图
  - search: 查询历史记录（如"今天吃了多少"、"上次喂奶是什么时候"）
- suggest: 成长建议相关意图
  - suggestion: 获取成长建议（如"宝宝最近食量怎么样"）
- conversation: 对话交流意图
  - reply: 闲聊对话（如"你好"、"谢谢"）
- exit: 退出意图
  - exit: 退出当前功能（如"退出"、"结束"）

请严格按照以下 JSON 格式返回结果：

**单事件格式（适用于大多数场景）：**
{{
    "target_type": "feeding|history|suggest|conversation|exit",
    "action": "start|end|one|search|suggestion|reply|exit",
    "event_name": "匹配到的事件名称（喂养场景必填，其他场景可为空）",
    "event_id": "匹配到的事件ID（喂养场景必填，其他场景可为空）",
    "quantity": 从用户输入中提取的数量值（如120，没有时省略或填null）,
    "event_type": "number|time|one（当事件不在可用列表中时，推断事件类型）",
    "event_unit": "ml|次|分钟|小时（当事件不在可用列表中时，推断事件单位）",
    "is_new_event": true|false（当事件不在可用列表中时，设为true）,
    "keywords": ["匹配到的关键词列表"],
    "content": "对话场景的回答内容（其他场景可为空）"
}}

**多事件格式（适用于包含多个喂养事件的场景）：**
{{
    "target_type": "feeding",
    "action": "multi",
    "event_name": "",
    "event_id": "",
    "events": [
        {{"action": "start|end|one", "event_name": "事件名称", "event_id": "事件ID", "quantity": 数量值}}
    ],
    "keywords": ["匹配到的关键词列表"],
    "content": ""
}}

事件类型推断规则（当事件不在可用列表中时）：
- 喂奶、喝水、喝奶粉 → number（数值型，单位：ml 或 次）
- 睡觉、游泳、洗澡、晒太阳 → time（时间型，单位：分钟 或 小时）
- 换尿布、刷牙、洗脸 → one（单次型，单位：次）

注意事项：
1. 如果无法确定意图，请使用 "conversation" + "reply"，并在 content 中说明无法理解
2. 喂养场景必须填写 event_name 和 event_id，event_id 从可用事件中选择
3. 当用户输入包含多个喂养事件时（如"没吃，睡着了"、"吃完奶，换了尿布"），请使用多事件格式
4. 多事件最多返回 3 个事件，超过时只取前 3 个
5. keywords 列表要包含用户输入中的关键信息
6. quantity 字段：从用户输入中提取具体数值，如"喝了120ml"返回120，"睡了两小时"返回120（分钟）
7. 如果事件名称不在可用列表中，请设置 is_new_event=true，并推断 event_type 和 event_unit
8. 返回结果必须是合法的 JSON 格式，不要有任何额外文字
"""


def build_intent_classification_user_message(text: str, event_dictionary: List[Dict[str, Any]]) -> str:
    """
    构建意图分类的用户消息

    业务逻辑：
    将用户输入和事件字典组合成完整的用户消息。

    Args:
        text: 用户输入的自然语言文本
        event_dictionary: 事件字典列表

    Returns:
        用户消息字符串
    """
    return f"""
请分析以下用户输入，识别其意图：

用户输入：{text}

可用事件类型：{json.dumps([e["event_name"] for e in event_dictionary], ensure_ascii=False)}
"""
