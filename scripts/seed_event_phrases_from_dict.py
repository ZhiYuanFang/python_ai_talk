"""
从事件字典生成短说法种子，写入 feeding_intents。

业务说明：
发版清空后执行：先 CLEAR_FEEDING_INTENTS_ON_STARTUP=true 启动清空，
再关开关，运行本脚本（或 Hub bulk）灌入 event_name / extra_names。
payload 形：{event_id, event_name, kind}。

用法（需可访问 history 字典 API 的环境）:
  python scripts/seed_event_phrases_from_dict.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# 仓库根加入 path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.feeding.services.event_cache import event_cache
from app.feeding.services.event_hierarchy import is_parent_event
from app.feeding.services.intent_cache_store import intent_cache_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_event_phrases")


async def main() -> None:
    full = await event_cache.get_full_event_dictionary()
    items = []
    for ev in full or []:
        eid = str(ev.get("event_id") or "").strip()
        ename = str(ev.get("event_name") or "").strip()
        if not eid or not ename:
            continue
        kind = "parent" if is_parent_event(eid, full) else "leaf"
        phrases = {ename}
        for x in ev.get("extra_names") or []:
            s = str(x or "").strip()
            if s:
                phrases.add(s)
        for doc in phrases:
            items.append(
                {
                    "document": doc,
                    "payload": {
                        "event_id": eid,
                        "event_name": ename,
                        "kind": kind,
                    },
                }
            )
    result = intent_cache_store.bulk_upsert(items)
    logger.info(
        "种子完成: added=%s skipped=%s failed=%s",
        result.get("added"),
        len(result.get("skipped") or []),
        len(result.get("failed") or []),
    )


if __name__ == "__main__":
    asyncio.run(main())
