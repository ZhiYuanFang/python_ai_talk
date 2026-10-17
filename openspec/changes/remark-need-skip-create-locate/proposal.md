## Why

「吃了120配方奶」已经由本地规则定成记一笔、事件和数量，仍会调用备注模型，模型只能返回空备注。落库时纯记一笔也会先问改删定位，而定位结果只用于修改和删除，这条新记录的时间仍由句中钟点决定。

## What Changes

- 备注在飞轮与备注模型之前判断是否还有明细。剥掉已定事件名、数量和记一笔套话后没有剩余描述时，备注为空，不查飞轮、不问模型、不把空备注写回飞轮。仍有描述则保持飞轮再到模型。别名已经带备注的路径不变。
- 本批没有修改也没有删除时，不调用改删定位。同一批里既有记一笔又有修改或删除时，仍只为修改和删除定位。
- 记一笔的开始时间继续由句中钟点写入新记录，不改为按最近一条覆盖旧记录。

## Capabilities

### New Capabilities

- `remark-need-local-rule`: 没有剩余明细时备注为空并跳过飞轮与备注模型
- `create-skip-locate`: 纯记一笔不进入改删定位，钟点仍写入新记录

### Modified Capabilities

- （无）当前基线 `openspec/specs/v0.0.1.md` 未要求备注先判断有无明细，也未禁止记一笔调用定位。

## Impact

- `app/feeding/services/segment_multidim.py` 备注分支
- `app/feeding/graphs/nodes/execute_history_crud.py` 中 `resolve_locate` 的调用条件
