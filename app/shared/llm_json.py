"""
LLM 返回类 JSON 的清洗与解析

业务说明：
模型常在「纯 JSON」里夹 //、/* */ 等注释，提示无法杜绝。
本模块在 json.loads 前做引号安全去注释，并剥 markdown 围栏。
供意图分类、澄清、护理留意、judge 等解析点共用。

设计思路：
1. 单遍扫描，跟踪双引号字符串与转义，避免误删 http://
2. 字符串外删除 // 行注释、/* */ 块注释、# 行注释
3. loads_llm_json：去围栏 → 去注释 → loads（失败可再抠首个 {...}）
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

# 从夹杂文本中抠首个 JSON 对象（兜底）
_JSON_OBJECT_RE = re.compile(r"\{[\s\S]*\}")


def strip_llm_json_comments(text: str) -> str:
    """
    去除 LLM JSON 文本中字符串外的注释。

    业务逻辑：
    - 双引号字符串内（含转义）原样保留，故 http:// 安全
    - 字符串外：// 至行尾、/* ... */、行首空白后的 # 至行尾

    Args:
        text: 原始或已去围栏的文本

    Returns:
        去注释后的文本
    """
    if not text:
        return ""
    out: list[str] = []
    i = 0
    n = len(text)
    in_string = False
    while i < n:
        ch = text[i]
        if in_string:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                # 保留转义对，避免 \" 提前结束字符串
                out.append(text[i + 1])
                i += 2
                continue
            if ch == '"':
                in_string = False
            i += 1
            continue

        # 字符串外
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue

        if ch == "/" and i + 1 < n:
            nxt = text[i + 1]
            if nxt == "/":
                # 行注释：跳到换行（保留换行便于定位）
                i += 2
                while i < n and text[i] not in "\r\n":
                    i += 1
                continue
            if nxt == "*":
                # 块注释
                i += 2
                while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                    i += 1
                i = i + 2 if i + 1 < n else n
                continue

        if ch == "#":
            # 仅当本行到 # 之前（本段输出末尾）全是空白时视为注释
            line_start = text.rfind("\n", 0, i) + 1
            prefix = text[line_start:i]
            # 已写入 out 的对应前缀也须为空白；用扫描起点更稳：
            # 简化：若 prefix 仅空白则跳过本行注释
            if prefix.strip() == "":
                # 还要确认 out 末尾对应本行未写入非空白——prefix 来自原 text 即可
                i += 1
                while i < n and text[i] not in "\r\n":
                    i += 1
                continue

        out.append(ch)
        i += 1

    return "".join(out)


def strip_markdown_fence(text: str) -> str:
    """去掉首尾 ``` / ```json 围栏。"""
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def loads_llm_json(raw: str) -> Any:
    """
    解析 LLM 返回的 JSON：去围栏 → 去注释 → loads。

    若整段失败，再尝试抠首个 {...} 后重复去注释并 loads。

    Args:
        raw: 模型原文

    Returns:
        json.loads 结果（通常为 dict / list）

    Raises:
        json.JSONDecodeError: 去注释后仍无法解析
        ValueError: 原文为空
    """
    text = strip_markdown_fence(raw or "")
    if not text:
        raise ValueError("LLM JSON 原文为空")

    cleaned = strip_llm_json_comments(text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = _JSON_OBJECT_RE.search(cleaned)
        if not match:
            raise
        excerpt = strip_llm_json_comments(match.group(0)).strip()
        return json.loads(excerpt)


def loads_llm_json_object(raw: str) -> Optional[Dict[str, Any]]:
    """
    解析为 dict；非对象或失败返回 None（供 care_alert 等软失败路径）。
    """
    try:
        data = loads_llm_json(raw)
    except (json.JSONDecodeError, ValueError, TypeError):
        return None
    if isinstance(data, dict):
        return data
    return None
