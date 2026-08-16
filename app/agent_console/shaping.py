"""
上游响应塑形（给 LLM 的瘦结果）

业务说明：
复用 baby_age / history_prompt_fields；options 只保留 id+name 等短字段。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.shared.baby_age import (
    age_band_from_months,
    age_months_from_profile,
    format_age_months_text,
)
from app.shared.history_prompt_fields import slim_history_events_for_prompt


def _unwrap_list(data: Any) -> List[Any]:
    """从 GoFrame 风格或裸 list 解出列表。"""
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("data", "list", "items", "rows", "events"):
            v = data.get(key)
            if isinstance(v, list):
                return v
            if isinstance(v, dict):
                for k2 in ("list", "items", "rows"):
                    if isinstance(v.get(k2), list):
                        return v[k2]
    return []


def _unwrap_obj(data: Any) -> Dict[str, Any]:
    """解出对象。"""
    if isinstance(data, dict):
        inner = data.get("data")
        if isinstance(inner, dict):
            return inner
        return data
    return {}


def shape_history_events(raw: Any, *, limit: int = 20) -> List[Dict[str, Any]]:
    """历史列表 → 瘦字段 + 可读时间。"""
    rows = _unwrap_list(raw)
    dicts = [x for x in rows if isinstance(x, dict)]
    return slim_history_events_for_prompt(dicts, limit=limit)


def shape_options(raw: Any) -> List[Dict[str, Any]]:
    """事件字典瘦身。"""
    rows = _unwrap_list(raw)
    out: List[Dict[str, Any]] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        eid = item.get("id", item.get("eventId", item.get("event_id")))
        name = item.get("name", item.get("eventName", item.get("event_name")))
        slim = {}
        if eid is not None:
            slim["id"] = eid
        if name is not None:
            slim["name"] = name
        # 常见辅助字段
        for k in ("unit", "eventUnit", "parentId", "parent_id"):
            if item.get(k) is not None:
                slim[k] = item[k]
        if slim:
            out.append(slim)
    return out


def shape_baby_profile(raw: Any) -> Dict[str, Any]:
    """画像 → 月龄等。"""
    profile = _unwrap_obj(raw)
    months = age_months_from_profile(profile)
    return {
        "ok": True,
        "ageMonths": months,
        "ageBand": age_band_from_months(months),
        "ageText": format_age_months_text(months),
        "birthdayKnown": months is not None,
        "gender": profile.get("gender") or profile.get("sex"),
    }


def shape_write_receipt(raw: Any) -> Dict[str, Any]:
    """写操作短回执。"""
    obj = _unwrap_obj(raw) if not isinstance(raw, dict) or "data" in (raw or {}) else (raw or {})
    if not isinstance(obj, dict):
        obj = {}
    rid = obj.get("id") or obj.get("Id") or obj.get("eventHistoryId")
    return {"ok": True, "id": rid if rid is not None else ""}
