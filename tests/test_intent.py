"""
意图分析单元测试

业务说明：
测试意图分析模块的核心功能，包括意图解析、事件匹配和兜底文案。
"""

import pytest
from app.api.routes import _parse_intent_result, _match_event_name, _get_default_conversation_reply


class TestIntentParsing:
    """意图解析测试"""

    def test_parse_valid_json(self):
        """测试解析有效JSON"""
        content = '{"target_type": "feeding", "action": "start", "event_name": "喂奶", "keywords": ["喂奶"], "content": ""}'
        result = _parse_intent_result(content)
        assert result["target_type"] == "feeding"
        assert result["action"] == "start"
        assert result["event_name"] == "喂奶"

    def test_parse_json_with_extra_text(self):
        """测试解析包含额外文本的JSON"""
        content = '思考：这是一个喂养意图。\n{"target_type": "feeding", "action": "start", "event_name": "喂奶", "keywords": ["喂奶"], "content": ""}'
        result = _parse_intent_result(content)
        assert result["target_type"] == "feeding"

    def test_parse_invalid_json(self):
        """测试解析无效JSON时返回默认值"""
        content = "无法理解用户意图"
        result = _parse_intent_result(content)
        assert result["target_type"] == "conversation"
        assert result["action"] == "reply"


class TestEventMatching:
    """事件匹配测试"""

    def test_match_event_name(self):
        """测试事件名称匹配"""
        event_dictionary = [
            {"event_name": "喂奶", "keywords": ["喂奶", "母乳", "吃奶"]},
            {"event_name": "喂奶粉", "keywords": ["奶粉", "奶瓶"]},
        ]
        result = _match_event_name("宝宝饿了，要喂奶", event_dictionary)
        assert result == "喂奶"

    def test_no_match_event_name(self):
        """测试无匹配事件名称"""
        event_dictionary = [
            {"event_name": "喂奶", "keywords": ["喂奶", "母乳"]},
        ]
        result = _match_event_name("宝宝今天睡得好吗", event_dictionary)
        assert result == ""


class TestDefaultReply:
    """兜底文案测试"""

    def test_greeting_reply(self):
        """测试问候语回复"""
        result = _get_default_conversation_reply("你好")
        assert "您好" in result

    def test_thanks_reply(self):
        """测试感谢回复"""
        result = _get_default_conversation_reply("谢谢")
        assert "不客气" in result

    def test_goodbye_reply(self):
        """测试告别回复"""
        result = _get_default_conversation_reply("再见")
        assert "再见" in result

    def test_other_reply(self):
        """测试其他情况回复"""
        result = _get_default_conversation_reply("天气真好")
        assert "母婴喂养" in result