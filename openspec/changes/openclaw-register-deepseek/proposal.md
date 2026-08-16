## Why

Gateway chat 报 `Unknown model: deepseek/deepseek-v4-flash`：agent 本地空 `models.json`（`providers: {}`）覆盖插件目录。需在 `openclaw.json5` 显式 `models.providers.deepseek` + defaults 登记 flash，使合并后仍有可用模型。

## What Changes

- `deploy/openclaw/openclaw.json5`：增加 `models.mode=merge` 与 `providers.deepseek`（含 v4-flash 等）；`agents.defaults.models` 登记 `deepseek/deepseek-v4-flash`。
- README 简述：改 json5 后 recreate；空 models.json 与显式登记的关系。
- 不改 Go；不强制改 Dockerfile entrypoint（本轮仅 json5）。

## Capabilities

### New Capabilities

- `openclaw-deepseek-provider-config`: OpenClaw 配置显式登记 DeepSeek provider 与 flash 模型。

### Modified Capabilities

- （无）

## Impact

- `openclaw.json5`、`README.md`
- 运维：recreate Gateway 容器使配置生效
