## Why

控制台 API 管理页要求为每个 History tool 填写完整上游 URL，但 README 未给出与 `go_ai_talk` 对齐的 path 表，也未说明应走 Go **主网关 `:9701`**（无用户 JWT）而非 **gateway-app `:9702`**，以及「上游 Bearer」对胖宝 history 应留空。运维/联调只能自行翻 Go 仓，易配错入口或误填日更用户 token。

## What Changes

- 在 `README.md`「管理页」相关章节补充：Catalog 槽位 ↔ Go history API 完整 path 对照表；推荐 `BASE`（主网关或直连 history-service）；明确勿用 gateway-app；上游 Bearer 对现网 history **留空**。
- 同步控制台页内 Go 接入说明（`_go_guide_markdown`），与 README 一致，避免页内仍无 path 指引。
- API 管理页对 guide **渲染 Markdown**（前端轻量库 vendoring `marked`，GFM 表格），不再 `textContent` 纯文本。
- **非 BREAKING**：不改 tools 路由或鉴权实现。

## Capabilities

### New Capabilities

- `console-upstream-docs`：文档与控制台说明 MUST 给出 Agent tools 上游 URL 填法（主网关基址、八槽位 path、上游 Bearer 语义）。

### Modified Capabilities

- （无）运行时行为不变；本变更不修改既有 history tools / 门禁 Requirement。

## Impact

- 文档：`README.md`
- 可选：`app/api/routes/agent_console.py` 中 `_go_guide_markdown`
- 无 API / DB / compose 行为变更
