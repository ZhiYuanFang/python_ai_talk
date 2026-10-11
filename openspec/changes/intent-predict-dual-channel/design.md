## Context

意图主图：`resolve_segments` → CRUD | `speak_history`。TYPE 维经 `feeding_type_cues` + TYPE 小 LLM（`target_type`/`op`/`history_mode`）。  
「还有多久睡觉/醒来」被打成 history 点查，优先已完成记录。  
Go：active-eta 已有 `GET /voice/internal/api/predict/active-eta`；imminent 仅 PUT+推送，`loadPredictImminentPending` 无私有对外读。  
算法仍在 Flutter；Python 只读 Redis。`predict-active-timing-eta` 仅增强「仅进行中」查史话术，与本预测问答分轨。

## Goals / Non-Goals

**Goals:**

- `target_type=predict`；**分维** `predict_channel`（active|next）与 `time_answer`（clock|remain），不合并。
- 两维由 TYPE LLM / 类型飞轮判定，非本地规则主路径。
- `speak_predict` 双通道拉数并播报；remain 超时：「已经过了预计时间」。
- 孪生 Go：imminent internal GET。

**Non-Goals:**

- Python/Go 重算 duration/nextAt；改推送闸；合并两维为单枚举；查史点查语义重写（仅防 predict 误入）；写测试。

## Decisions

### D1：意图模型与路由

- `TargetType` 增加 `predict`。
- 顶层（或段草稿）字段：`predict_channel`、`time_answer`；仅 `target_type=predict` 时必填合法值，否则清空。
- `predict` 时 `op` 空、`history_mode` 空；EVENT 维仍解析事件（如睡眠）。
- 图：`target_type=predict` → `speak_predict` → END（不进 `speak_history` / CRUD）。

**Alternatives：** 塞进 `history_mode=predict`——否决（易回落查史）。合并 `predict_mode` 四值——否决（产品要求两维分离）。

### D2：TYPE 飞轮 / LLM（判定权威）

- `feeding_type_cues` payload 扩展：`predict_channel`、`time_answer`；`allowed` 含 `predict`。
- TYPE LLM 一次输出：`target_type`、`op`、`history_mode`、`predict_channel`、`time_answer`、`need_confirm`、`keywords[]`。
- 提示词纠偏：过去时长/上次用时 → history；「还有多久醒来/睡觉」「几点醒/睡」→ predict + 对应两维；不确定 `need_confirm=true`。
- **禁止**本地主路径：多久→history、醒来→active、几点→clock 等词表短路。
- 写入时机同现网 TYPE：高置信立即灌库；需确认则确认后按 keywords 写。
- SSE：`stream(thinking_enabled=True)`，中文 reasoning。

**Alternatives：** 独立 PREDICT 小 LLM——否决（多一跳；TYPE 已含 target）。

### D3：双通道 HTTP

| channel | 调用 | 锚点字段 |
|---------|------|----------|
| active | 已有 active-eta GET | `expectEndAt`（unix 秒） |
| next | **新** `GET {voice}/voice/internal/api/predict/imminent/pending?deviceNo=` | `nextAt` |

- 鉴权：`X-Device-Gateway-Internal-Secret`（复用 settings）。
- 响应：GoFrame `data`；imminent 建议 `{ "events": [ ... ] }`，字段对齐 App PUT（eventId/nextAt/title/expect*）。
- 匹配：按段事件 id 与目录归根，对齐 root/leaf/eventId（active 复用 active-eta 匹配辅助思路）。

### D4：播报与超时

- `clock`：墙钟「预计约 HH:mm …」（结束/开始语依 channel）；时区 `shanghai_tz`。
- `remain`：相对时长（可复用现有时分口吻）；**超时**（now 严格晚于锚点）：**「已经过了预计时间」**（不用「 · 已超时」）。
- 无匹配/GET 失败/缺密钥：估不准类中文；**MUST NOT** 改念「上一次…用时」。

### D5：与查史 / 仅进行中 ETA

- `history`+`speak_history` 不变。
- 「仅进行中」active-eta 增强可保留，服务真·点查仅进行中。
- predict 句不得被 `history_mode_cues`「多久」门闩改回 history（predict 优先）。

### D6：孪生仓

- **Go（必做）**：imminent internal GET + InternalSecretMiddleware；空键 `events:[]`。
- **Flutter**：无算法改动；保证 imminent/active-eta 同步仍触发即可。
- **Python Hub**：类型向量 admin 展示/校验新字段（若页已存在）。

## Risks / Trade-offs

- [冷启动 TYPE 仍把「还有多久」打成 history] → 提示词拆语义 + Hub 灌短关键字种子；飞轮纠正。
- [imminent 无 internal GET 时 next 全降级] → Go 同发或先发；Python next 失败走估不准。
- [事件 id 根/叶不一致] → 匹配归根；多条取最近未来 nextAt / 匹配叶或根的 active。
- [未配密钥] → 双通道均降级，不拖垮意图整轮。

## Migration Plan

1. Go 上 imminent internal GET。  
2. Python：枚举/飞轮/TYPE LLM/`speak_predict`/路由。  
3. 可选 bulk 种子：「还有多久醒来」→ active+remain 等。  
4. 回滚：去掉 predict 路由即可；Redis 键无破坏。

## Open Questions

（无；2026-10-11 探索已敲定：两维不合并、飞轮判定、remain 超时文案、接受 target_type=predict。）
