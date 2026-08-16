## 1. README

- [x] 1.1 在 `README.md` §3 管理页扩展：推荐 BASE（`:9701` 主网关 / 直连 `:9801`）、禁止 gateway-app、上游 Bearer 留空
- [x] 1.2 写入八槽位 Catalog key ↔ Method ↔ path 对照表（可抄完整 URL）

## 2. 控制台说明

- [x] 2.1 更新 `_go_guide_markdown`：与 README 同语义的基址、path 表、Bearer 留空说明
- [x] 2.2 扩展 guide：能力（intent/clinic/care_alert）、调用方式、完整 `http(s)://` 参考 URL；按 Request 推导本服务基址

## 3. Guide Markdown 渲染

- [x] 3.1 Vendor `marked.min.js` 到 `app/agent_console/static/vendor/`，并增加 `/console/vendor/marked.min.js` 路由
- [x] 3.2 `index.html` 引入 marked；`app.js` 用 GFM 渲染 `#goGuide`；调整 `.guide` 样式

## 4. 校验

- [x] 4.1 `openspec validate readme-console-go-upstream-urls --strict`
