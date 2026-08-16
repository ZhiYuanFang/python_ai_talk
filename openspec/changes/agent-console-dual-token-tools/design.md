## Context

OpenClaw Gateway 已是编排权威；插件 `pangbao-tools` 将 history 直打 Go 且原样回传，塑形逻辑仍留在 Python（`baby_age`、`history_prompt_fields`）但无调用方。对外开放与多租户需要：统一 Agent 数据面、按 Token 路由完整 URL、可运营后台。OpenClaw 发行版多为单 `gateway.auth.token`，多 G 须由我方门禁承接。实施顺序：**先 Python，再 Go**。

## Goals / Non-Goals

**Goals:**

- History 读/写经 Python tools，出口为 LLM 瘦 JSON（月龄、可读时间、字段裁剪）。
- 插件仅 `toolsBaseUrl`；废除产品路径上的 `historyBaseUrl` 直打。
- MySQL（与 Go 同址）存 G/A 1:1、tool 槽位完整 URL；无默认胖宝 Go 域名。
- 多 G 门禁 + A 驱动上游；G 失效则智能体不可用；无 A/未配 URL 则 CRUD 类 tools 失败。
- 管理后台：主页仅 G/A Token 入 API 页；管理员成对签发与 G 生效/失效；API 页双 Token 复制 + Go 接入说明 + 契约。
- 视觉：品牌「AI喂养智能体」、浅空蓝主色、宝宝主题插画氛围。

**Non-Goals:**

- 本期不改 OpenClaw 上游源码以支持原生多 token。
- 不实现任意字段映射 DSL（客户 API 应对齐 Catalog 瘦契约或可适配的 Raw 信封）。
- 不把飞轮 BYO 给客户（飞轮仍可本机 Python）。
- 不在本 change 强制完成 Go 全部联调（tasks 末段预留；Python 先可门禁+tools 自测）。
- 不写自动化测试文件。

## Decisions

### 1. 形态 2：读写都经 Python

- **选择**：所有 `history_*` / `baby_profile` 由插件打 Python；Python 调租户配置的完整 URL，再塑形返回。
- **替代**：写直打 Go + 读经 Python → BYO 双基址、塑形输入绑死胖宝 Go 字段。
- **替代**：插件内 TS 塑形 → 与 Python 双份逻辑，不利于复用现有模块。

### 2. G / A 强制 1:1

- **选择**：成对签发；一张 G 仅绑一张 A。
- **替代**：G 一对多 A → 管理与 Go 配置更复杂，已由产品否决。

### 3. 多 G 用门禁代理

- **选择**：对外验 DB 中 enabled 的 G；通过后用内部单 secret 调本机 Gateway；A 经约定请求头（如 `x-pangbao-api-token`）由插件转发到 Python。
- **替代**：每客独立 Gateway 进程 → 运维过重。
- **替代**：等上游多 token → 阻塞产品。

### 4. 无默认业务上游

- **选择**：settings/env **不**提供胖宝 Go 默认 `HISTORY`/`GO_API`；未配置槽位则 tool 明确失败。
- **替代**：env 默认公网 Go → 与「真正可自定义」冲突。

### 5. 主页仅 Token 进入

- **选择**：G 或 A 任一有效即可进入该对的 API 管理页；取消用户名入口。
- **理由**：降低凭用户名枚举/误入风险。

### 6. 后台与 tools 同进程或同仓模块

- **选择**：控制面 API + 静态/模板前端落在本仓 FastAPI（路径如 `/console`），共享 DB 访问层。
- **替代**：独立前端仓 → 可后置；本期减少仓库分裂。

### 7. Tool Contract Catalog

- **选择**：槽位名与入参/出参/必填由仓库内静态 Catalog（JSON/YAML/代码常量）驱动配置页说明书；租户只填完整 URL（+ 可选上游鉴权头）。
- **替代**：租户自填 schema → LLM tool 参数与客户 API 易漂移。

### 8. 清理范围

- **选择**：保留并接线 `baby_age` / `history_prompt_fields`；`http_client` 收敛为「按 URL 调用上游」；删除插件 Go path、无用 `OPENCLAW_GATEWAY_URL`（Python）、Care 飞轮死配置等与本能力冲突的残留。
- **时机**：在 shaped tools 可运行后执行，避免误删塑形库。

## Risks / Trade-offs

- [OpenClaw 不转发自定义头] → Spike 插件/ctx；不行则用 session 元数据或门禁把 A 注入内部调用约定。
- [多一跳延迟] → 接受；监控 Python→上游超时。
- [客户 API 字段不合 Catalog] → 文档要求 Adapter；失败返回可读错误给模型。
- [Token 明文在 API 页可复制] → 会话需登录态；展示默认遮罩；仅哈希入库。
- [共享 MySQL] → 表前缀 `agent_`；迁移由本仓负责；权限最小化。
- [废止直打 Go 与旧 design 冲突] → 本 change 为权威后续。

## Migration Plan

1. 部署 MySQL 表 + 管理员种子；内部 Gateway secret。
2. 上线 Python（tools 塑形 + 门禁 + console）；插件改只打 `toolsBaseUrl`。
3. 管理员为胖宝成对签发 G/A，在 API 页手填原 Go URL。
4. 门禁对外替换直连 Gateway；验证 G 失效与无 A 行为。
5. Go 配置 G+A 与头转发后切流。
6. 回滚：插件临时恢复直打（不推荐）或门禁回退单静态 G；数据表保留。

## Open Questions

- 门禁进程：嵌入 FastAPI vs 独立小服务（默认倾向同仓 FastAPI 反代/转发到 Gateway）。
- 上游 Raw 是否允许「胖响应由 Python 映射」vs「强制瘦响应」（默认：读路径 Python 尽力塑形；写回执统一瘦）。
- API 页展示 G/A 明文是否需二次确认（默认：遮罩 + 一键复制）。

## Spike 结论（任务 3.3）

- OpenClaw 插件 `execute(ctx)` **不保证**稳定暴露入站 `x-pangbao-api-token`。
- **落地**：优先从 `ctx.headers` 读取；若空则回退进程环境 `PANGBAO_API_TOKEN`（单租户 Gateway 进程可注入）。
- **推荐生产**：门禁后按会话/租户把 A 注入 Gateway 侧环境或后续做「每租户 Gateway 配置」；Go 二期必须同时传 G（门禁 Bearer）与 A（独立头），并在联调中验证头是否到达 plugin。
