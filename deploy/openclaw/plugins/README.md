# Pangbao OpenClaw tools 插件

任务 **2.1 / 2.2 / 2.3**：`api.registerTool`（经 `defineToolPlugin`）注册 history 四写+只读、飞轮、Care 出卡。

## 安装

```bash
cd deploy/openclaw/plugins/pangbao-tools
npm install
npm run build
# 在 Gateway 配置目录（含 openclaw.json5）下：
openclaw plugins install ./plugins/pangbao-tools
openclaw doctor
```

环境变量：

| 变量 | 含义 |
|------|------|
| `PANGBAO_HISTORY_BASE_URL` | Go 基址（默认 `http://127.0.0.1:8001`） |
| `PANGBAO_HISTORY_TOKEN` | 可选 Bearer |
| `PANGBAO_TOOLS_BASE_URL` | Python `/v1` 基址（飞轮/出卡） |

## Tool → 后端

| Tool | 后端 |
|------|------|
| `history_create/update/delete/end_latest` | Go `/device/history/api/event/*` |
| `history_filter/list/options`、`baby_profile` | Go 只读 |
| `flywheel_intent_*`、`flywheel_clinic_*`、`clinic_judge_implicit_acceptance` | Python `/v1/tools/*` |
| `emit_care_cards` | Python `/v1/tools/care/emit_cards` |

**ACL**：写史仅 Intent `tools.allow`；Clinic/Care 不得包含 `history_create|update|delete|end_latest`。Care **无**飞轮 tool。
