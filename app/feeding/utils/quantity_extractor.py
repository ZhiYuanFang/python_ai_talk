"""
数量提取工具模块

业务说明：
从用户输入的自然语言文本中提取数量值，支持汉字数字和阿拉伯数字两种格式。
用于向量匹配节点的前置数量提取，避免通用场景请求 LLM 导致接口延迟。

设计思路：
1. 先进行汉字数字到阿拉伯数字的替换
2. 再使用正则表达式提取数字
3. 支持常见的数量单位（ml、分钟、次等）上下文判断
"""

import logging
import re
from typing import Optional

# 初始化日志记录器
logger = logging.getLogger(__name__)

# 汉字数字到阿拉伯数字的映射表
CHINESE_NUMERALS = {
    "一": "1",
    "二": "2",
    "两": "2",
    "三": "3",
    "四": "4",
    "五": "5",
    "六": "6",
    "七": "7",
    "八": "8",
    "九": "9",
    "十": "10",
}

# 用于匹配阿拉伯数字的正则表达式
# 支持整数，可带单位（ml、分钟、次、小时等）
ARABIC_NUMBER_PATTERN = re.compile(r"\d+")


def _replace_chinese_numerals(text: str) -> str:
    """
    将文本中的汉字数字替换为阿拉伯数字。

    业务逻辑：
    遍历汉字数字映射表，将文本中出现的汉字数字逐个替换为对应的阿拉伯数字。
    替换顺序按汉字数字长度降序，避免短字符提前替换导致长字符无法匹配。

    Args:
        text: 原始用户输入文本

    Returns:
        替换后的文本
    """
    # 按汉字数字长度降序排序，避免 "十二" 被拆成 "1" + "二"
    for chinese, arabic in sorted(CHINESE_NUMERALS.items(), key=lambda x: len(x[0]), reverse=True):
        text = text.replace(chinese, arabic)
    return text


def extract_quantity_from_text(text: str) -> Optional[int]:
    """
    从用户输入文本中提取数量值。

    业务逻辑：
    1. 先将汉字数字转换为阿拉伯数字
    2. 使用正则表达式提取文本中的数字
    3. 返回第一个匹配到的数字作为数量值
    4. 如果未匹配到任何数字，返回 None

    使用场景：
    - 向量匹配节点在高置信度匹配后，提取用户输入中的数量
    - 避免通用场景中请求 LLM 导致接口延迟

    Args:
        text: 用户输入的自然语言文本

    Returns:
        提取到的数量值（整数），未提取到时返回 None

    Side Effects:
        无
    """
    if not text or not text.strip():
        return None

    # 步骤1：汉字数字转换
    normalized_text = _replace_chinese_numerals(text)

    # 步骤2：正则提取阿拉伯数字
    match = ARABIC_NUMBER_PATTERN.search(normalized_text)
    if match:
        try:
            quantity = int(match.group())
            logger.debug(f"数量提取成功: text='{text[:30]}...', quantity={quantity}")
            return quantity
        except ValueError:
            logger.warning(f"数量提取转换失败: matched='{match.group()}'")
            return None

    # 未匹配到数字
    logger.debug(f"数量提取未命中: text='{text[:30]}...'")
    return None
