## 1. 配置与拉取

- [x] 1.1 `settings`：增加 `voice_service_url`（`VOICE_SERVICE_URL`）与内部密钥配置（对齐 Go `DEVICE_GATEWAY_INTERNAL_SECRET`）；`.env.example` / 部署说明补齐若缺
- [x] 1.2 `http_client`：`GET {voice}/voice/internal/api/predict/active-eta?deviceNo=`，头 `X-Device-Gateway-Internal-Secret`；解包 `data.items`；中文注释；失败向上抛或返回空由调用方降级
- [x] 1.3 匹配辅助：history 行 `id`/`Id`→`historyId`，再 `leafEventId`，再目录归根 `rootEventId`；`expectEndAt`/`startAt` 按 unix 秒解析

## 2. 意图播报

- [x] 2.1 `speak_history`：仅当点查走「仅进行中」时拉一次 ETA，传入 `_format_only_in_progress`
- [x] 2.2 拼接「预计约 HH:mm 结束」（`shanghai_tz`）；`now > expectEndAt` 时追加「 · 已超时」（对齐 App）
- [x] 2.3 GET/无匹配/解析失败：保持原「正在进行中」话术，不失败整轮意图

## 3. 验收

- [ ] 3.1 手工：设备有进行中 + Redis 有匹配 ETA → intent 点查答含「预计约」与时刻
- [ ] 3.2 手工：ETA 已过期 → 答含「 · 已超时」或「已超时」
- [ ] 3.3 手工：GET 不可用或未配密钥 → 仍答「正在进行中」类原话术
