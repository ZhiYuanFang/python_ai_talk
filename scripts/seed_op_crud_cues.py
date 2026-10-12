"""
OP / R·source 整段飞轮种子

业务说明：
灌入常用整句：睡着了→create；睡醒了→update；睡了多久了→read+record；
还有多久醒来→read+predict。短关键词 TYPE 种子不再写入。

用法：
  python scripts/seed_op_crud_cues.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.feeding.services.op_cue_store import op_cue_store
from app.feeding.services.read_source_cue_store import read_source_cue_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_op_crud_cues")

# (整句, op_rail, read_source|None)
_SEEDS = [
    ("睡着了", "create", None),
    ("宝宝睡着了", "create", None),
    ("吃了120", "create", None),
    ("吃了120毫升", "create", None),
    ("换尿布了", "create", None),
    ("睡醒了", "update", None),
    ("醒了", "update", None),
    ("宝宝睡醒了", "update", None),
    ("睡了多久了", "read", "record"),
    ("睡了多久", "read", "record"),
    ("上次吃了多少", "read", "record"),
    ("还有多久醒来", "read", "predict"),
    ("还有多久睡觉", "read", "predict"),
    ("几点醒", "read", "predict"),
    ("删除刚才那条", "delete", None),
    ("退出", "exit", None),
]


def main() -> int:
    op_entries = [
        {"document": doc, "payload": {"op_rail": rail}}
        for doc, rail, _rs in _SEEDS
    ]
    op_result = op_cue_store.bulk_upsert(op_entries)
    logger.info(
        "OP 种子: added=%s skipped=%s failed=%s",
        op_result.get("added"),
        len(op_result.get("skipped") or []),
        len(op_result.get("failed") or []),
    )
    rs_entries = [
        {"document": doc, "payload": {"read_source": rs}}
        for doc, _rail, rs in _SEEDS
        if rs
    ]
    rs_result = read_source_cue_store.bulk_upsert(rs_entries)
    logger.info(
        "R·source 种子: added=%s skipped=%s failed=%s",
        rs_result.get("added"),
        len(rs_result.get("skipped") or []),
        len(rs_result.get("failed") or []),
    )
    failed = (op_result.get("failed") or []) + (rs_result.get("failed") or [])
    for f in failed:
        logger.warning("失败条目: %s", f)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
