# 手工验收清单（任务 6.3 / 7.3）

## Python

1. 配置 MySQL + `AGENT_ADMIN_*` + `INTERNAL_GATEWAY_*`，启动服务。
2. 打开 `/console` → 管理员登录 → 成对签发 → 复制 G/A。
3. 用 G 或 A 进入 API 页，为各 history tool 填完整 URL（可先填胖宝 Go 原 path）。
4. `POST /v1/tools/history/filter` 不带头 → 401；带头 A 但未配 URL → `ok:false` 未配置。
5. 配好 URL 后 filter/profile 返回瘦字段 / ageMonths。
6. 管理员将 G 设失效 → `POST /agent-gate/v1/chat/completions` Bearer 该 G → 401。

## Go

1. `OPENCLAW_GATEWAY_URL` 指向门禁；`OPENCLAW_GATEWAY_TOKEN=<G>`；`PANGBAO_API_TOKEN=<A>`。
2. 正常对话；关 G → 智能体不可用；清空 A → history tools 失败。
