## Context

intent 主图：`resolve_segments` → `speak_history` | CRUD。进行中仅有记录时用 `_format_only_in_progress`。  
孪生 Go 已落地：Redis 权威列表 + App PUT +  
`GET /voice/internal/api/predict/active-eta?deviceNo=`（voice-service，`InternalSecretMiddleware`）。  
Flutter 同步字段与文案函数 `formatActiveTimingEtaLabel` 为对齐基准。

## Goals / Non-Goals

**Goals:**

- 拉 ETA；在「仅进行中」播报拼接预计结束与超时标记。
- 失败降级；契约字段与 Go/Flutter 一致。

**Non-Goals:**

- 重挂 `in_progress_probe`/`classify_intent`；改 tip/clinic；写测试；服务端重算 duration。

## Decisions

### D1：挂点

仅增强 `speak_history` 进行中固定话术 `_format_only_in_progress`（叶子点查与父塌缩同类分支）。  
不改 `_format_typed_clause` 的「上一次…正在进行中」边角路径；不改 daily / 段多维主路径。

拉取时机：本轮点查出现 `only_open` 时再 GET（整设备一次），列表传入格式化；勿在同步 formatter 内反复请求。

### D2：HTTP 契约（对照 Go 已实现）

- **基址**：`settings.voice_service_url` ← 环境变量 `VOICE_SERVICE_URL`（勿打到 `history_service_url`）。
- **方法/路径**：`GET {voice}/voice/internal/api/predict/active-eta?deviceNo=`
- **鉴权**：请求头 `X-Device-Gateway-Internal-Secret`，值与 Go `DEVICE_GATEWAY_INTERNAL_SECRET` 同源配置（Settings 新增字段；缺省则 GET 失败→降级，不得拖垮意图）。
- **响应**：GoFrame `{ code, message, data: { items: [...] } }`；用现有 `_unwrap_go_data` 后取 `items`（**不是** `list`）。
- **空语义**：缺键 / 空 / 非法 JSON 在 Go 侧已变空 `items`；Python 视同无 ETA。

**Item 字段（与 Go `PredictActiveEtaItem` / Flutter 对齐）：**

| JSON | 类型 | 说明 |
|------|------|------|
| `rootEventId` | int | 根事件 id，>0 |
| `leafEventId` | int | 叶子 id（Go 表内去重键），>0 |
| `historyId` | string，可缺 | 历史行 id；空串当无 |
| `title` | string，可缺 | 展示名；播报可不依赖 |
| `startAt` | int | 开始 **unix 秒** |
| `expectEndAt` | int | 预计结束 **unix 秒**；已过期仍可能出现 |

### D3：匹配顺序

对当前播报的 history 行依次尝试，命中则用其 `expectEndAt`：

1. **`historyId`**：`str(row.id 或 row.Id).strip()` 与 item.`historyId` 相等（两边均非空）。
2. **`leafEventId`**：`row.eventId` / `event_id` 与 item.`leafEventId`（数值或十进制字符串等价）。
3. **`rootEventId`**：由事件目录对叶子归根，再与 item.`rootEventId` 比。

说明：Go 同表按 `leafEventId` 去重；Flutter 同步按根只留一条进行中 → root 兜底歧义低。`historyId` 可空（乐观/未落库 id）时依赖 leaf 即可。

### D4：文案（对齐 App）

与 Flutter `formatActiveTimingEtaLabel` 一致：

- 未超时：`预计约 HH:mm 结束`（墙钟；本仓用 `shanghai_tz`，与现有 intent 一致；App 为设备 local，东八区等价）。
- 超时：`now > expectEndAt`（严格晚于，对齐 `DateTime.isAfter`）时拼接 **` · 已超时`**（中间点+两侧空格），完整为  
  `预计约 HH:mm 结束 · 已超时`。
- 拼在「正在进行中」之后，例如：  
  `…正在进行中，预计约 15:30 结束` /  
  `…正在进行中，预计约 15:30 结束 · 已超时`。

### D5：降级

GET 失败（含缺密钥/网络/非 2xx）、空列表、无匹配：保持现有「正在进行中」句，不抛错中断意图整轮。

## Risks / Trade-offs

- [陈旧 ETA] → 仍可能播报；以 history 仍进行中为前提（与 Go「不过滤过期」一致）。
- [未配内部密钥] → 恒降级无 ETA；部署须注入与 voice 相同的 secret。
- [时区非东八] → 与 App local 可能差一截；本迭代接受上海墙钟。

## Migration Plan

Go GET / Flutter PUT 已就绪；本仓合并后手工验 GET+播报。无 Redis 数据则降级，可单独上线。

## Open Questions

（无；2026-10-11 对照 Go/Flutter 已实现回写契约。）
