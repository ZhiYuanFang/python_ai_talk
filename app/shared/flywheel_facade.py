"""
飞轮门面（我方托管聚合）

业务说明：
Intent / Clinic 仅经本门面读写飞轮；Care **无**飞轮。
FLYWHEEL_BASE_URL 为空时走进程内实现（当前 Chroma）。
非空时预留 HTTP 客户端（后续独立 Flywheel Cloud）。

Intent / Clinic 仓互不写入对方。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.config.settings import settings

logger = logging.getLogger(__name__)


def flywheel_base_locked() -> str:
    """返回配置的飞轮基址（可空）；业务 GO_API 不得覆盖此值。"""
    return (settings.flywheel_base_url or "").strip().rstrip("/")


def portable_intent_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    将 Intent 缓存载荷改为可移植结构。

    业务逻辑：
    去掉 events[].event_id（跨租户不可复用）；保留 name/op/action/top_k 等；
    命中后再经当前事件字典解析 id。
    """
    out = dict(payload or {})
    events = out.get("events")
    if isinstance(events, list):
        portable_events: List[Dict[str, Any]] = []
        for ev in events:
            if not isinstance(ev, dict):
                continue
            item = {k: v for k, v in ev.items() if k != "event_id"}
            portable_events.append(item)
        out["events"] = portable_events
    return out


class FlywheelFacade:
    """
    飞轮统一入口。

    业务说明：
    retrieve / record_outcome 按 agent 分仓；进程内委托既有 store。
    """

    def retrieve_intent(
        self, query: str, *, n_results: int = 1
    ) -> List[Dict[str, Any]]:
        """检索 Intent 意图缓存仓。"""
        from app.feeding.services.intent_cache_store import intent_cache_store

        if flywheel_base_locked():
            logger.debug("飞轮远程基址已配置，本期仍走进程内 Intent 仓")
        return intent_cache_store.search(query, n_results=n_results)

    def record_intent_outcome(
        self,
        document: str,
        payload: Dict[str, Any],
    ) -> Optional[str]:
        """
        写入 Intent 飞轮（强制可移植：去掉 event_id）。
        """
        from app.feeding.services.intent_cache_store import intent_cache_store

        return intent_cache_store.add(document, portable_intent_payload(payload))

    def record_clinic_accepted_qa(
        self,
        *,
        standalone_question: Optional[str],
        answer: Optional[str],
        age_band: Optional[str],
    ) -> Optional[str]:
        """Clinic 隐式采纳后推广 Q&A。"""
        from app.shared.qa_fast_path import promote_accepted_qa

        return promote_accepted_qa(
            standalone_question=standalone_question,
            answer=answer,
            age_band=age_band,
        )


flywheel = FlywheelFacade()
