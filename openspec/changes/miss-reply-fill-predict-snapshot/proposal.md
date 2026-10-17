## Why

落库成功会删掉预测快照。兜底回答只读 Redis，读到空就告诉模型「无预测算法快照」，不再重算。前端也会直接改记录，不能靠 Python 增删改去刷新快照，所以删除保持不动，缺快照时改由兜底自己生成。

## What Changes

- 增删改落库成功后仍删除整份 `predict_algo:{设备}`。TTL 仍是 10 分钟。问预测的读写不变。
- 兜底回答发现没有快照（没有键，或 `by_root` 为空）时，先按问预测同一套近 7 日间隔算法生成快照并写入，再用这份快照回答。
- 生成失败或没有任何成功的根时，兜底仍按现在的「无快照」继续，不把异常当成用户可见失败。已有快照时不重算。

## Capabilities

### New Capabilities

- `miss-reply-fill-predict-snapshot`: 兜底回答在没有预测快照时先生成再答

### Modified Capabilities

- 无。基线 `openspec/specs/v0.0.1.md` 没有「兜底无快照则重算」的既有需求。

## Impact

- `app/feeding/services/agent_miss_soft_reply.py`：读空时触发生成。
- `app/feeding/graphs/nodes/speak_predict.py` 与 `app/feeding/services/predict_algo.py`：复用近 7 日间隔算法，供兜底写入快照。
- `app/feeding/graphs/nodes/execute_history_crud.py` 的删除快照逻辑不改。
