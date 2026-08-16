## REMOVED Requirements

### Requirement: Python /v1/analyze/intent 为意图产品入口
**Reason**: 编排改 OpenClaw Gateway；Go 不再调用 Python 意图 HTTP。
**Migration**: Go 改调 Gateway Intent agent；删除或停用 `/v1/analyze/intent` 与 stream 作为产品入口。

### Requirement: 结构化意图响应信封为 Go 落库依据
**Reason**: Intent 对 Go 仅 NL reply；落库经 Gateway tools。
**Migration**: 删除 Go 对 `target_type`/`events[]`/`need_confirm` 的产品依赖。
