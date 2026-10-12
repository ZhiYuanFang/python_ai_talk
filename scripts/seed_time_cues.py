"""
时间相对配方飞轮种子

业务说明：
向 feeding_time_cues 灌入整句 document + 相对配方。
可重复执行：同 document 由 bulk 跳过。

用法：
  python scripts/seed_time_cues.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.feeding.services.time_cue_store import time_cue_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_time_cues")

# 整句种子：(document, formula)
_SEEDS = [
    (
        "昨晚八点喂了",
        {
            "kind": "instant",
            "points": [
                {
                    "day": "yesterday",
                    "period": "evening",
                    "hour": 20,
                    "minute": 0,
                }
            ],
            "duration_minutes": None,
        },
    ),
    (
        "昨天晚上八点吃了奶",
        {
            "kind": "instant",
            "points": [
                {
                    "day": "yesterday",
                    "period": "evening",
                    "hour": 20,
                    "minute": 0,
                }
            ],
            "duration_minutes": None,
        },
    ),
    (
        "今天早上七点换尿布",
        {
            "kind": "instant",
            "points": [
                {
                    "day": "today",
                    "period": "morning",
                    "hour": 7,
                    "minute": 0,
                }
            ],
            "duration_minutes": None,
        },
    ),
]


def main() -> int:
    entries = [
        {"document": doc, "payload": formula} for doc, formula in _SEEDS
    ]
    result = time_cue_store.bulk_upsert(entries)
    logger.info(
        "时间配方种子完成: added=%s skipped=%s failed=%s",
        result.get("added"),
        len(result.get("skipped") or []),
        len(result.get("failed") or []),
    )
    for f in result.get("failed") or []:
        logger.warning("失败条目: %s", f)
    return 0 if not (result.get("failed") or []) else 1


if __name__ == "__main__":
    raise SystemExit(main())
