"""
查史播报策略飞轮种子（硬切整段）

业务说明：
向 feeding_history_speak_cues 灌入整句 document。
短关键词种子已废弃。可重复执行：同 document 由 bulk 跳过。

用法：
  python scripts/seed_history_speak_cues.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.feeding.services.history_speak_cue_store import history_speak_cue_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_history_speak_cues")

# 整句种子：(document, point_pick, open_speak)
_SEEDS = [
    ("睡了多久了", "latest", "elapsed"),
    ("睡了多久", "latest", "elapsed"),
    ("宝宝睡了多久了", "latest", "elapsed"),
    ("上次睡眠多久", "prefer_completed", "in_progress"),
    ("上一次睡觉是什么时候", "prefer_completed", "in_progress"),
]


def main() -> int:
    removed = history_speak_cue_store.clear_short_documents()
    logger.info("已清除短词条目: %s", removed)
    entries = [
        {
            "document": doc,
            "payload": {"point_pick": pp, "open_speak": os_},
        }
        for doc, pp, os_ in _SEEDS
    ]
    result = history_speak_cue_store.bulk_upsert(entries)
    logger.info(
        "整句种子完成: added=%s skipped=%s failed=%s",
        result.get("added"),
        len(result.get("skipped") or []),
        len(result.get("failed") or []),
    )
    for f in result.get("failed") or []:
        logger.warning("失败条目: %s", f)
    return 0 if not (result.get("failed") or []) else 1


if __name__ == "__main__":
    raise SystemExit(main())
