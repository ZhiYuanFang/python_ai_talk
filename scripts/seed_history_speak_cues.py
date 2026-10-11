"""
查史播报策略飞轮种子

业务说明：
向 feeding_history_speak_cues 灌入常用短线索。
「多久了」类 → latest + elapsed；「上次」类 → prefer_completed + in_progress。
可重复执行：同 document 由 bulk 跳过。

用法：
  python scripts/seed_history_speak_cues.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# 保证以仓库根为 cwd 时可 import app
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.feeding.services.history_speak_cue_store import history_speak_cue_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_history_speak_cues")

# 种子：(document, point_pick, open_speak)
_SEEDS = [
    ("多久了", "latest", "elapsed"),
    ("睡了多久", "latest", "elapsed"),
    ("睡了多久了", "latest", "elapsed"),
    ("多长时间了", "latest", "elapsed"),
    ("上次", "prefer_completed", "in_progress"),
    ("上一次", "prefer_completed", "in_progress"),
    ("上次睡眠", "prefer_completed", "in_progress"),
]


def main() -> int:
    entries = [
        {
            "document": doc,
            "payload": {"point_pick": pp, "open_speak": os_},
        }
        for doc, pp, os_ in _SEEDS
    ]
    result = history_speak_cue_store.bulk_upsert(entries)
    logger.info(
        "种子完成: added=%s skipped=%s failed=%s",
        result.get("added"),
        len(result.get("skipped") or []),
        len(result.get("failed") or []),
    )
    for f in result.get("failed") or []:
        logger.warning("失败条目: %s", f)
    return 0 if not (result.get("failed") or []) else 1


if __name__ == "__main__":
    raise SystemExit(main())
