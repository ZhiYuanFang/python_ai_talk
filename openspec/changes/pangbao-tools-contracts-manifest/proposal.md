## Why

Gateway chat 在 DeepSeek 已通后仍失败：`No callable tools remain after resolving explicit tool allowlist`。`pangbao-tools` 显示 `Status: loaded` 但 `Shape: non-capability`；OpenClaw ≥2026.5 要求 manifest 声明 `contracts.tools` 显式工具名，否则 `registerTool` 被静默拒绝。当前仅有顶层 `tools` 数组，不足以让 history/flywheel/care 工具进入 agent 表面。

## What Changes

- 更新 `deploy/openclaw/plugins/pangbao-tools/openclaw.plugin.json`：增加 `contracts.tools`，列出与插件实现一致的全部工具名（与现有顶层 `tools` 对齐）。
- 可选保留顶层 `tools` 以兼容发现；以 `contracts.tools` 为注册权威。
- README / 插件 README 一句说明：改 manifest 后 restart Gateway；OpenClaw 需 `contracts.tools`。
- 不改 tool 实现源码、不改 agents.allow、不改 Python。

## Capabilities

### New Capabilities

- `pangbao-tools-manifest-contracts`: pangbao-tools 插件 manifest 通过 `contracts.tools` 声明工具所有权，使 Gateway 能将 allowlist 中的业务 tool 解析为可调用。

### Modified Capabilities

- （无）

## Impact

- `deploy/openclaw/plugins/pangbao-tools/openclaw.plugin.json`
- 运维文档（根 README 或 `plugins/README.md`）
- 部署：同步 manifest 后 recreate/restart Gateway（volume 挂载，一般不必 rebuild 镜像）
