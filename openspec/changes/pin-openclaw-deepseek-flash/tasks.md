## 1. 门禁剥离注模头

- [x] 1.1 `agent_gate.py`：透传列表移除 `x-openclaw-model`；中文注释说明产品写死 flash、忽略 Go 注模
- [x] 1.2 确认仍透传 `x-openclaw-session-key`、`x-pangbao-api-token`

## 2. OpenClaw 钉死模型

- [x] 2.1 `openclaw.json5`：`agents.defaults` 增加 `model`（primary 或字符串）为 `deepseek/deepseek-v4-flash`；必要时给三个 agent 同步（以 schema 可启动为准）

## 3. README

- [x] 3.1 更新根 `README.md`：写死 flash、门禁忽略 `x-openclaw-model`、`body.model` 仍选 agent

## 4. 校验

- [x] 4.1 `openspec validate pin-openclaw-deepseek-flash --strict`
