## Why

「睡着了」和本地记一笔规则里的「睡了」不是同一串字，操作轨因此去问顶层轨模型。备注剥套话时也剥不掉「睡着了」，空明细仍会再问备注模型。

## What Changes

- 记一笔本地规则增加「睡着了」。没有疑问词时判为 create，不再查操作飞轮、不再问顶层轨模型。
- 备注是否还有明细时，把「睡着了」和「睡了」一样剥掉。剥完没有剩余描述则备注为空，不查备注飞轮、不问备注模型。
- 「睡醒了」仍是结束计时，不并进记一笔。「睡了多久」仍是查记录。事件名仍走词典与说法飞轮，不在本变更里把「睡着了」写成某个事件的别名。

## Capabilities

### New Capabilities

- `asleep-local-create`: 「睡着了」由本地规则记成记一笔，并且不因此抽取备注

### Modified Capabilities

- （无）当前基线 `openspec/specs/v0.0.1.md` 未把「睡着了」列为记一笔或备注套话。

## Impact

- `app/feeding/services/dim_local_rules.py` 的记一笔规则
- `app/feeding/services/segment_remark.py` 的明细剥除
