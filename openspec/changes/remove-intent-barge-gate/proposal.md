## Why

同一设备上有一轮意图还标着进行中时，后到的句子被插话闸门挂起，不再进入意图图。占坑方若中途断开或进程重启，匣会停在 `running`，之后每次说话又把过期时间续满，这个设备号就一直进不了图。

## What Changes

- **BREAKING**：删除设备级意图闸门。同步与流式意图分析都直接跑本句的图，不再因同设备已有进行中的一轮而挂起。
- 删除占坑、插话缓冲、挂起等待终局，以及覆盖缺口时把新旧句拼起来重跑。
- 不再读写 `intent_barge:{device_no}`。已卡住的键不再被咨询。
- 确认、消歧仍按各自 `conversation_id` 续聊，不靠这只匣。

## Capabilities

### New Capabilities

- `intent-independent-run`: 每次意图分析只解析本句并跑自己的图，同设备的另一句不得把它挡在图外

### Modified Capabilities

- （无）当前基线 `openspec/specs/v0.0.1.md` 未收录设备单飞与插话拼接。进行中的 `intent-barge-in-buffer` 行为由本变更撤回。

## Impact

- `app/api/routes/intent.py`：同步与流式入口去掉占坑、挂起和拼接重跑
- 删除 `app/feeding/services/intent_barge.py` 与 `app/feeding/services/intent_barge_store.py`
- 同设备两句可以同时落库，不再串行
