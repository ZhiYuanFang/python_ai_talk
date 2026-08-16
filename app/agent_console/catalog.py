"""
Tool 契约 Catalog（静态）

业务说明：
配置页只读展示入参/出参/必填；槽位名与插件 tool 名对齐。
租户只配置完整 URL，不改字段语义。
"""

from __future__ import annotations

from typing import Any, Dict, List

# 槽位定义：key 用于 DB agent_tool_endpoint.tool_key
TOOL_CATALOG: List[Dict[str, Any]] = [
    {
        "key": "history_create",
        "method": "POST",
        "title": "新增历史事件",
        "description": "Intent 写史：create",
        "params": [
            {"name": "deviceNo", "required": True, "desc": "设备号"},
            {"name": "eventId", "required": True, "desc": "事件字典 id"},
            {"name": "eventName", "required": False, "desc": "事件名"},
            {"name": "eventUnit", "required": False, "desc": "单位"},
            {"name": "eventNumber", "required": False, "desc": "数量"},
            {"name": "startTime", "required": False, "desc": "开始时间戳"},
            {"name": "endTime", "required": False, "desc": "结束时间戳"},
            {"name": "remark", "required": False, "desc": "备注"},
            {"name": "action", "required": False, "desc": "start|one|end"},
        ],
        "response": [
            {"name": "ok", "required": True, "desc": "是否成功"},
            {"name": "id", "required": False, "desc": "上游记录 id（若有）"},
        ],
    },
    {
        "key": "history_update",
        "method": "POST",
        "title": "修改历史事件",
        "description": "Intent 写史：update",
        "params": [
            {"name": "deviceNo", "required": True, "desc": "设备号"},
            {"name": "id", "required": True, "desc": "历史记录 id"},
            {"name": "eventNumber", "required": False, "desc": "数量"},
            {"name": "startTime", "required": False, "desc": "开始"},
            {"name": "endTime", "required": False, "desc": "结束"},
            {"name": "remark", "required": False, "desc": "备注"},
        ],
        "response": [
            {"name": "ok", "required": True, "desc": "是否成功"},
        ],
    },
    {
        "key": "history_delete",
        "method": "POST",
        "title": "删除历史事件",
        "description": "Intent 写史：delete",
        "params": [
            {"name": "deviceNo", "required": True, "desc": "设备号"},
            {"name": "id", "required": True, "desc": "历史记录 id"},
        ],
        "response": [
            {"name": "ok", "required": True, "desc": "是否成功"},
        ],
    },
    {
        "key": "history_end_latest",
        "method": "POST",
        "title": "结束最近未闭合事件",
        "description": "Intent 写史：end-latest",
        "params": [
            {"name": "deviceNo", "required": True, "desc": "设备号"},
            {"name": "eventId", "required": False, "desc": "事件 id"},
            {"name": "endTime", "required": False, "desc": "结束时间"},
        ],
        "response": [
            {"name": "ok", "required": True, "desc": "是否成功"},
        ],
    },
    {
        "key": "history_filter",
        "method": "GET",
        "title": "筛选历史",
        "description": "读史；Python 塑形后回瘦 events",
        "params": [
            {"name": "deviceNo", "required": True, "desc": "设备号"},
            {"name": "eventIds", "required": False, "desc": "事件 id 列表"},
            {"name": "startTime", "required": False, "desc": "窗起"},
            {"name": "endTime", "required": False, "desc": "窗止"},
            {"name": "limit", "required": False, "desc": "条数上限"},
            {"name": "remark", "required": False, "desc": "备注过滤"},
            {"name": "ignoreTimeRange", "required": False, "desc": "忽略时间窗"},
        ],
        "response": [
            {"name": "events", "required": True, "desc": "瘦历史列表"},
            {"name": "ok", "required": True, "desc": "是否成功"},
        ],
    },
    {
        "key": "history_list",
        "method": "GET",
        "title": "分页历史列表",
        "description": "读史列表；塑形",
        "params": [
            {"name": "deviceNo", "required": True, "desc": "设备号"},
            {"name": "page", "required": False, "desc": "页码"},
            {"name": "pageSize", "required": False, "desc": "页大小"},
        ],
        "response": [
            {"name": "events", "required": True, "desc": "瘦历史列表"},
            {"name": "ok", "required": True, "desc": "是否成功"},
        ],
    },
    {
        "key": "history_options",
        "method": "GET",
        "title": "事件可选项",
        "description": "事件字典；瘦为 id+name 等",
        "params": [],
        "response": [
            {"name": "options", "required": True, "desc": "精简选项列表"},
            {"name": "ok", "required": True, "desc": "是否成功"},
        ],
    },
    {
        "key": "baby_profile",
        "method": "GET",
        "title": "宝宝画像",
        "description": "生日等；Python 推导 ageMonths",
        "params": [
            {"name": "deviceNo", "required": True, "desc": "设备号"},
        ],
        "response": [
            {"name": "ageMonths", "required": False, "desc": "月龄，未知可空"},
            {"name": "ageBand", "required": False, "desc": "月龄带"},
            {"name": "ageText", "required": True, "desc": "文案"},
            {"name": "birthdayKnown", "required": True, "desc": "是否已知生日"},
            {"name": "ok", "required": True, "desc": "是否成功"},
        ],
    },
]


def catalog_by_key() -> Dict[str, Dict[str, Any]]:
    """tool_key → 条目。"""
    return {str(item["key"]): item for item in TOOL_CATALOG}
