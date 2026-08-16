## Context

生产 Gateway（openclaw@2026.7.1-2）上 `pangbao-tools`：

- `plugins list` / inspect：`Status: loaded`，`Source: .../dist/index.js`
- `Shape: non-capability`，`Capability mode: none`
- `node_modules/typebox` 与 `dist/index.js` 存在
- chat 仍报 allowlist 与 registered 交集为空

根因对齐上游行为（≥2026.5.2）：agent tools 须在 `openclaw.plugin.json` 的 **`contracts.tools`** 中列出精确名称；仅顶层 `tools` 或 `contracts.tools: true` 不够，`registerTool` 静默失败。

## Goals / Non-Goals

**Goals:**

- Manifest 声明完整 `contracts.tools`，与 `defineToolPlugin` 注册的 name 一致。
- restart 后 intent/clinic/care_alert 的 `tools.allow` 能命中至少部分（理想为全部）已注册业务 tool，不再因「零 callable」在 prompt 阶段硬失败。

**Non-Goals:**

- 不改 `src/index.ts` 业务逻辑、HTTP 路径、A Token 转发。
- 不改 `openclaw.json5` agents allow（除非验收证明命名不一致）。
- 不升级 OpenClaw 版本；不把插件烤进镜像（仍 volume）。

## Decisions

### D1: 在现有 manifest 增加 `contracts.tools`，保留顶层 `tools`

- **选择**：`contracts.tools` = 当前顶层 `tools` 同名数组；保留顶层 `tools` 以免破坏旧发现路径。
- **备选**：删除顶层 `tools` 只留 contracts → 可能丢兼容；本轮不冒险。
- **禁止**：`contracts.tools: true`（上游已确认无效）。

### D2: 改 manifest 即可，不必 rebuild dist

- 契约在 json 清单；运行时 register 仍由 `dist/index.js` 执行。同步文件 + Gateway restart。

### D3: 文档一句验收

- `plugins inspect` / chat 不再 `No callable tools remain`；若仍 non-capability 但 tools 非空，以 callable 为准。

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 仍 non-capability 且 tools 空 | 核对 contracts 名字与代码 `name:` 完全一致；查 gateway 是否仍报 missing contracts |
| allow 含未声明名 | contracts 覆盖插件全部 tool；allow 是子集即可 |
| 云上未同步文件 | README 提醒 sync + restart |

## Migration Plan

1. 合并 → 部署同步 `openclaw.plugin.json` → `compose up -d --force-recreate`（或 restart）。
2. curl intent；期望越过 allowlist 空错误。
3. 回滚：恢复旧 manifest。

## Open Questions

- 无；若 restart 后仍空，再查 `defineToolPlugin` 与 capability shape（次轮）。
