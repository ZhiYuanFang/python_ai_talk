## Why

前端已将非流式 `POST /v1/analyze/intent` 当作陪伴续聊入口使用，不再需要经此路径做喂养意图分析。语义上应属 clinic，但 URL 不能挪；故在原路径上改为直接调用 clinic agent 并返回结果。

## What Changes

- **BREAKING**：非流式 `/v1/analyze/intent` 不再执行 pending 澄清、父消歧、向量匹配、意图分类或喂养后处理。
- 该接口 SHALL 直接调用与意图图中相同的 clinic agent 路径（`call_clinic_agent`），以 `IntentResponse` 返回（`target_type=conversation`，`action=reply`，`content` 为 clinic 回答）。
- URL 与请求体（`text` / `device_no` / `model`）保持不变，兼容现有前端。
- `/v1/analyze/intent/stream` **不改**，仍走意图分析图。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `intent-analysis`：非流式 `/v1/analyze/intent` 改为 clinic 陪伴同步回答，不再做喂养等意图分类。

## Impact

- 代码：`app/api/routes/intent.py` 的 `analyze_intent`；复用 `call_clinic_agent`。
- API：**BREAKING** 行为——「开始喂奶」等不再返回 feeding 结构，而是 clinic 口语回答。
- `/intent/stream`、intent_graph、feeding 管道逻辑保留供流式使用。
- 不生成测试文件。
