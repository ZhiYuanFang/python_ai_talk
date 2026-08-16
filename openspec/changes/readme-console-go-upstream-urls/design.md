## Context

控制台按 A Token 为每个 tool 槽位存完整 URL + 可选 `upstream_auth`。Python 无默认 Go 域名。兄弟仓 `go_ai_talk` 中：

- **gateway-service `:9701`**：反代 `/device/history/api/*`，无 App Bearer
- **gateway-app `:9702`**：多数 history API 需用户 JWT
- **history-service `:9801`**：领域实现，无 Bearer

Agent tools 应对齐主网关或直连 history；上游 Bearer 对现网应留空（非用户日更 token）。

## Goals / Non-Goals

**Goals:**

- README（及控制台 Go 说明）可抄填八槽位完整 URL
- 写明 BASE 推荐与上游 Bearer 语义，避免配错 gateway-app

**Non-Goals:**

- 不改 `call_upstream` / 透传用户 JWT
- 不改 Go 网关鉴权
- 不引入默认业务域名 env

## Decisions

1. **文档权威落在 README §3 扩展**，附完整对照表；控制台 `_go_guide_markdown` 同步摘要（含 path 表或指向 README 同表），避免只改一处。
2. **BASE 示例**用占位 `http://<Go主网关主机>:9701`，并注明可直连 `http://history-service:9801`（须网络可达）；明确禁止把默认 App 公网/`9702` 当 Agent 上游。
3. **八槽位**与 Catalog / Go `AGENTS.md` 四 REST + filter/list/options/birthday 对齐。
4. **Guide 渲染**：vendor `marked` 至 `app/agent_console/static/vendor/marked.min.js`，经 `/console/vendor/marked.min.js` 提供；`app.js` 用 `marked.parse`（GFM）写入 `#goGuide`。guide 仅服务端常量，不解析租户输入；调整 `.guide` 样式去掉不适配 HTML 的 `pre-wrap`。
5. **Guide 内容**：能力（intent/clinic/care_alert）+ 调用方式 + 完整 `http(s)://` URL；`tenant/me` 根据 `Request` 推导本服务公网基址（`X-Forwarded-Proto`/`Host`），写入门禁与控制台示例；上游 Go 仍用 `http://<Go主机>:9701` 占位。

## Risks / Trade-offs

- [主网关 history 无用户鉴权] → 文档写明属服务间调用既有模型；勿把用户 JWT 塞上游 Bearer
- [BASE 随部署变化] → 用占位符 + 两种推荐形态，不写死公网域名
- [MD→HTML XSS] → guide 非用户可控；后续若 guide 可配置再加 DOMPurify
- [Forwarded Host 被伪造] → 仅用于说明文案展示，不参与鉴权
