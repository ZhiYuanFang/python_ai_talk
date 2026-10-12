"""
分层整段飞轮金线种子

业务说明：
覆盖 OP / R·source / history_speak / predict 金线话术。
硬切整段；可重复执行（同 document 跳过）。

用法：
  python scripts/seed_dim_flywheel_cues.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.feeding.services.history_speak_cue_store import history_speak_cue_store
from app.feeding.services.op_cue_store import op_cue_store
from app.feeding.services.predict_cue_store import predict_cue_store
from app.feeding.services.read_source_cue_store import read_source_cue_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_dim_flywheel_cues")

_OP = [
    ("睡着了", "create"),
    ("睡醒了", "update"),
    ("睡了多久了", "read"),
    ("还有多久醒来", "read"),
    ("删除刚才那条", "delete"),
]
_SOURCE = [
    ("睡了多久了", "record"),
    ("还有多久醒来", "predict"),
    ("还有多久睡觉", "predict"),
]
_SPEAK = [
    ("睡了多久了", "latest", "elapsed"),
    ("宝宝睡了多久了", "latest", "elapsed"),
]
_PREDICT = [
    ("还有多久醒来", "active", "remain"),
    ("还有多久睡觉", "next", "remain"),
    ("几点醒", "active", "clock"),
]


def main() -> int:
    n_short = history_speak_cue_store.clear_short_documents()
    logger.info("清除 speak 短词: %s", n_short)

    r1 = op_cue_store.bulk_upsert(
        [{"document": d, "payload": {"op_rail": r}} for d, r in _OP]
    )
    r2 = read_source_cue_store.bulk_upsert(
        [{"document": d, "payload": {"read_source": s}} for d, s in _SOURCE]
    )
    r3 = history_speak_cue_store.bulk_upsert(
        [
            {"document": d, "payload": {"point_pick": p, "open_speak": o}}
            for d, p, o in _SPEAK
        ]
    )
    r4 = predict_cue_store.bulk_upsert(
        [
            {
                "document": d,
                "payload": {"predict_channel": c, "time_answer": t},
            }
            for d, c, t in _PREDICT
        ]
    )
    for name, res in (
        ("OP", r1),
        ("source", r2),
        ("speak", r3),
        ("predict", r4),
    ):
        logger.info(
            "%s: added=%s skipped=%s failed=%s",
            name,
            res.get("added"),
            len(res.get("skipped") or []),
            len(res.get("failed") or []),
        )
    failed = []
    for res in (r1, r2, r3, r4):
        failed.extend(res.get("failed") or [])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
