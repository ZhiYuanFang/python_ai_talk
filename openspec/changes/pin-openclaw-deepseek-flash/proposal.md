## Why

产品临时要求 Intent/Clinic/Care 编排 LLM **一律**使用 `deepseek/deepseek-v4-flash`，不再跟随 Go 经 `x-openclaw-model` 的选型。Go 仓先不动：其注模头可继续发送，但必须对运行时无效。仅改默认 primary 不够，因 OpenClaw 会优先采用请求头 override。

## What Changes

- `deploy/openclaw/openclaw.json5`：`agents.defaults.model`（及必要时各 agent）钉死 `deepseek/deepseek-v4-flash`。
- `app/api/routes/agent_gate.py`：转发 Gateway 时 **不再透传** `x-openclaw-model`，使 Go 注入无效。
- 根 `README.md`：说明产品写死 flash、门禁忽略 Go 注模头；`body.model`（`openclaw/intent` 等）仍选 agent。
- **不改** `go_ai_talk`。
- **不改** Python 飞轮侧 LLM key / `llm_client`。

## Capabilities

### New Capabilities

- `pinned-gateway-llm`: 门禁忽略上游 LLM 注模头；OpenClaw 三 agent 默认 LLM 固定为 DeepSeek V4 Flash。

### Modified Capabilities

- （无独立基线 capability 目录需 delta；行为以本 change 增量规格为准，收版时并入版本基线。）

## Impact

- 文件：`agent_gate.py`、`openclaw.json5`、`README.md`
- 运行：VIP/车道选模不再影响 Gateway 实际 LLM；额度逻辑仍在 Go，与所用模型可能暂时不一致（已知产品取舍）
- 运维：改 json5 后需重启/recreate OpenClaw 容器；无需改 Go 配置
