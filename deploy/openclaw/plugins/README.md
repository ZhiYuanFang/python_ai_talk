# pangbao-tools

OpenClaw 插件：全部 tools 打 Python `toolsBaseUrl`（`/v1/tools/*`）。

- History / baby_profile：需请求头或环境 `PANGBAO_API_TOKEN`（A）；Python 按控制台配置的完整 URL 转发并塑形。
- 已废弃 `historyBaseUrl` 直打 Go。
- **`openclaw.plugin.json` 必须含 `contracts.tools`（显式工具名数组）**，否则 OpenClaw ≥2026.5 会静默拒绝 `registerTool`，chat 报 `No callable tools remain` / `no registered tools matched`。勿写 `contracts.tools: true`。
- 仅改 manifest：同步后 **restart / recreate Gateway** 即可，一般不必 rebuild 镜像；改 `src/` 仍需 `npm run build`。

```bash
npm install && npm run build
```

自检：restart 后对 `openclaw/intent` 再 chat，不应再出现上述零 callable 错误（Python/上游业务错另论）。
