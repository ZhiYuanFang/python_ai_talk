## Why

意图智能体点查历史时，若仅有进行中计时，现话术只说「正在进行中」，无法回答「大概何时结束」。Go voice-service 已提供进行中 ETA internal GET；本仓须在 intent 的 `speak_history` 路径消费并对齐 App 超时文案。

## What Changes

- `settings` / `http_client`：按 `VOICE_SERVICE_URL` 调用  
  `GET /voice/internal/api/predict/active-eta?deviceNo=`，请求头带  
  `X-Device-Gateway-Internal-Secret`（与 Go `DEVICE_GATEWAY_INTERNAL_SECRET` 对齐）；解包 GoFrame `data.items`。
- 在 `speak_history`「仅进行中」播报（`_format_only_in_progress`）中拼接预计结束；超时追加与 App 一致的「 · 已超时」；GET 失败或无匹配项时保持现有话术（降级）。
- 按 **`historyId` → `leafEventId` → `rootEventId`** 与 history 行对齐（history 行 `id`/`Id` 字符串化比对 `historyId`；叶子用 `eventId`；根经事件目录归根）。
- **不**重挂已下线的 `classify_intent` / `in_progress_probe` 图节点；本迭代不改 tip/clinic。
- 孪生：`flutter_ai_talk` / `go_ai_talk` 同名 change（Go/Flutter 已实现同步侧；本仓消费）。

## Capabilities

### New Capabilities

- `intent-active-timing-eta`：intent 播报消费进行中 ETA 的行为约定。

### Modified Capabilities

（无独立基线 capability 名则仅用新 capability；若仓库已有 intent-speak 相关名，实现时以本 change spec 为准。）

## Impact

- 代码：`app/config/settings.py`（`voice_service_url`、内部密钥）、`app/shared/http_client.py`、`speak_history.py`（及少量辅助格式化/匹配）；中文业务注释；`.env.example` / 部署说明补密钥若缺。
- 不新建测试文件。
