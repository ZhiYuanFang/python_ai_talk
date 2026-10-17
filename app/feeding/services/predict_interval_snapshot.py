"""
近 7 日间隔预测

业务说明：
问预测与兜底补快照共用这里的计算。可跳过 Redis 读取。
只把 status=ok 的根写进设备快照。预约约定不在这里生成。
"""

from __future__ import annotations

import logging
from datetime import datetime as dt
from typing import Any, Dict, List, Optional

from app.feeding.services.appointment_event import event_is_appointment_flag
from app.feeding.services.event_hierarchy import (
    get_descendant_leaves,
    is_parent_event,
)
from app.feeding.services.predict_algo import (
    PredictToolResult,
    filter_records_for_root,
    half_life_days_for_age_months,
    predict_next_for_records,
    prediction_seven_day_unix_bounds,
)
from app.feeding.services.predict_algo_cache import predict_algo_cache
from app.shared.history_window import shanghai_tz
from app.shared.http_client import http_client

logger = logging.getLogger(__name__)


def catalog_roots(full_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """字典里 parent_id 为空的根。子事件不单独算一条。"""
    roots: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for ev in full_events or []:
        if not isinstance(ev, dict):
            continue
        eid = str(ev.get("event_id") or "").strip()
        if not eid or eid in seen:
            continue
        if ev.get("parent_id") not in (None, ""):
            continue
        seen.add(eid)
        roots.append(ev)
    return roots


def leaf_ids_for_root(root_id: str, full_events: List[Dict[str, Any]]) -> List[str]:
    """算法轨拉史：根下全部叶子；根本身是叶则返回该 id。"""
    rid = str(root_id or "").strip()
    if not rid:
        return []
    if not is_parent_event(rid, full_events):
        return [rid]
    leaves = get_descendant_leaves(rid, full_events)
    ids = [str(x.get("event_id") or "").strip() for x in leaves]
    return [x for x in ids if x] or [rid]


async def baby_age_months(device_no: str) -> Optional[int]:
    """从画像推月龄；失败返回 None，调用方改用默认半衰期。"""
    try:
        profile = await http_client.get_baby_profile(device_no)
        if not isinstance(profile, dict):
            return None
        for key in ("months", "ageMonths", "age_months"):
            if profile.get(key) is not None:
                return int(profile[key])
        birth = profile.get("birthDate") or profile.get("birth_date")
        if birth:
            tz = shanghai_tz()
            if isinstance(birth, (int, float)):
                bdt = dt.fromtimestamp(float(birth), tz=tz)
            else:
                s = str(birth).strip()[:10]
                bdt = dt.strptime(s, "%Y-%m-%d").replace(tzinfo=tz)
            now = dt.now(tz=tz)
            months = (now.year - bdt.year) * 12 + (now.month - bdt.month)
            if now.day < bdt.day:
                months -= 1
            return max(0, months)
    except Exception as exc:
        logger.debug("画像月龄不可用: %s", exc)
    return None


async def compute_interval_tool(
    *,
    device_no: str,
    root_id: str,
    event_name: str,
    full_events: List[Dict[str, Any]],
    write_cache: bool = True,
    half_life_days: Optional[int] = None,
) -> PredictToolResult:
    """
    近 7 日拉史并计算一个根的间隔预测。不读快照。

    write_cache 为真且 status=ok 时写入该根。拉史失败当空样本继续算。
    """
    start_u, end_u = prediction_seven_day_unix_bounds()
    leaf_ids = leaf_ids_for_root(root_id, full_events)
    try:
        rows = await http_client.get_filtered_history_events(
            device_no,
            event_ids=leaf_ids or [root_id],
            start_time=start_u,
            end_time=end_u,
            limit=500,
        )
    except Exception as exc:
        logger.warning("近 7 日拉史失败: %s", exc)
        rows = []
    scoped = filter_records_for_root(rows or [], root_id, full_events)
    if half_life_days is None:
        months = await baby_age_months(device_no)
        half_life_days = half_life_days_for_age_months(months)
    tool = predict_next_for_records(
        event_id=root_id,
        event_name=event_name,
        records=scoped,
        catalog=full_events,
        half_life_days=half_life_days,
    )
    if write_cache and tool.status == "ok":
        await predict_algo_cache.put_root(
            device_no, root_id, tool.to_prompt_dict()
        )
    return tool


async def fill_interval_snapshot(device_no: str) -> Optional[Dict[str, Any]]:
    """
    快照整份缺失时，按字典每个非预约根重算并写入。

    字典不可用、单个根失败都吞掉。没有任何成功根时返回当前读取结果（可能为空）。
    """
    dn = str(device_no or "").strip()
    if not dn:
        return None
    try:
        from app.feeding.services.event_cache import event_cache

        full = await event_cache.get_full_event_dictionary()
    except Exception as exc:
        logger.warning("兜底补快照读取事件字典失败: %s", exc)
        return None
    if not full:
        logger.info("兜底补快照：事件字典为空")
        return None
    months = await baby_age_months(dn)
    half = half_life_days_for_age_months(months)
    wrote = 0
    for root in catalog_roots(full):
        if event_is_appointment_flag(root):
            continue
        rid = str(root.get("event_id") or "").strip()
        name = str(root.get("event_name") or "").strip()
        try:
            tool = await compute_interval_tool(
                device_no=dn,
                root_id=rid,
                event_name=name,
                full_events=full,
                write_cache=True,
                half_life_days=half,
            )
        except Exception as exc:
            logger.warning("兜底补快照单根失败 root=%s err=%s", rid, exc)
            continue
        if tool.status == "ok":
            wrote += 1
    logger.info("兜底补快照完成 device=%s ok_roots=%s", dn, wrote)
    return await predict_algo_cache.get(dn)
