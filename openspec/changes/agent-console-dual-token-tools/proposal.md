## Why

Gateway 插件当前将 history 直打 Go 且原样回传，缺少旧图中的月龄推导与历史裁剪，导致 LLM 上下文膨胀且 BYO 困难；同时缺乏可运营的控制面：多调用方 Gateway Token（G）与落库路由 API Token（A）无法自助配置，Python 仍暗示默认接入胖宝 Go。需要把「读写经 Python 塑形 + 双 Token 注册表 + 智能体管理后台」一次定清，并先落 Python、后改 Go。

## What Changes

- **BREAKING**：废止「History CRUD tools 由 Gateway 直打 Go」；history 读/写一律经 Python `/v1/tools/*`，插件仅配置 `toolsBaseUrl`。
- Python 在 tool 出口复用/挂接既有塑形（`baby_age`、`history_prompt_fields` 等），回给 LLM 瘦 JSON；**无** `GO_API`/`HISTORY` 默认业务域名。
- 引入与 Go **同址 MySQL** 的租户注册：`G Token`（调智能体资格，可生效/失效）与 `A Token`（tools 落库路由）**强制 1:1**；成对签发。
- 门禁承载**多 G**（OpenClaw 进程仍可用内部单 secret）；请求须带有效 G 才能用智能体；缺有效 A 或未配 URL 则 CRUD/读史类 tools 失败。
- 智能体管理后台（品牌「AI喂养智能体」、浅空蓝+宝宝主题）：主页仅 **G 或 A Token** 进入 API 管理页；右上管理员账密；API 页展示并可复制 G+A、Go 接入说明、各 tool 完整 URL 与契约说明书。
- 清理直打 Go 残留与无用 env（在塑形/注册表落地后）；`http_client` 改为上游调用实现而非删除塑形库。
- **分期**：本仓先完成 Python（tools + DB + 后台 + 门禁）；Go 分项配置 G/A 与头转发列为后续任务（可同 change 末段或依赖本仓就绪）。

## Capabilities

### New Capabilities

- `shaped-history-tools`：History 读写经 Python tools、LLM 侧瘦响应、插件只打 toolsBaseUrl、废止直打 Go。
- `agent-tenant-tokens`：G/A 1:1、MySQL 注册表、无默认上游、G 生效失效、tools 按 A 解析 URL。
- `gateway-multi-token-gate`：多 G 门禁代理/校验，内部转单 token Gateway。
- `agent-console`：管理后台 IA/主题、主页 Token 入 API 页、管理员台、Go 视角接入说明与契约展示。
- `go-dual-token-client`：Go 分别配置并发送 G 与 A（二期）。

### Modified Capabilities

- （基线为单文件 `v0.0.1.md`；本变更以新 capability spec 为准，收版时合并。显式废止进行中/已完成 change 中「history 直打 Go」设计决策。）

## Impact

- 代码：`app/api/routes/openclaw_tools.py`、`http_client`/`baby_age`/`history_prompt_fields`、新 console/DB/gate 模块；`deploy/openclaw/plugins/pangbao-tools`、`openclaw.json5`；`.env*` / compose 去掉默认业务上游。
- 兄弟仓 Go：二期改 OpenClaw 客户端头与配置项。
- 运维：需 MySQL、门禁与 Gateway 同部署；胖宝 Go URL 仅经后台手配。
