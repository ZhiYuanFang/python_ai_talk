## Why

说「尿尿了」时，入库回执是「已记录 尿尿 1」。一次性事件的 `eventNumber` 固定为 1，只为落库，不该念给用户听。

## What Changes

- 叶子类型为 `one` 时，成功回执不拼接 `eventNumber`。新增说「已记录尿尿。」，修改说「已修改尿尿。」。
- 计量事件仍报数量和单位，例如「已记录配方奶 120ml」。
- 落库的 `eventNumber` 保持现状：`one` 的新增和删除仍写 1。
- 删除回执本来就不带数量，保持不变。

## Capabilities

### New Capabilities

- `one-event-receipt-omit-number`: 一次性事件的入库成功回执不念 eventNumber

### Modified Capabilities

- （无）当前基线 `openspec/specs/v0.0.1.md` 未单独描述这条回执文案。

## Impact

- `app/feeding/services/history_crud.py`：组批次时带上叶子类型；`render_persist_content` 对 `one` 不拼数量。
- 发给 Go 的 batch 字段不变，类型只留在本地下划线字段，不进请求体。
