## Context

`speak_history` 点查经 `_pick_completed_or_only_open` 无条件优先已完成，再才退回进行中；「睡了多久了」在存在进行中睡眠时会答上一笔完整用时。TYPE 飞轮已承载 `target_type`/`op`/`history_mode`/`predict_*`；产品要求查史**选行**与**进行中话术**另开独立飞轮，缺维走 LLM，禁止静默默认旧策略。

约束：中文注释；禁止自动测试；SSE `stream(thinking_enabled=True)` + 中文 reasoning；提示词在 `prompts/system.py`；不写 rule_gap。

## Goals / Non-Goals

**Goals:**

- 独立集合 + 小 LLM：`point_pick` × `open_speak`。
- 点查（history + point）播报前解析两维；落地选行与拼句。
- 缺维/非法 → 必调 LLM；热路径关键字命中跳过 LLM。
- Admin API；不写缺口箱。

**Non-Goals:**

- 不把两维塞进 `feeding_type_cues` / TYPE LLM。
- 不改 daily 汇总、predict 路径、CRUD。
- 不让 LLM 看历史行或猜库；策略维仅表达句意偏好。
- 本仓不实现 Go Hub 前端（tasks 标兄弟仓）。
- 不为策略维强制用户确认（默认直播）。

## Decisions

### D1：独立集合，不扩 TYPE

集合名：`feeding_history_speak_cues`（可微调）。document = 短关键字；payload = `{point_pick, open_speak}`。与 `feeding_intents` / `feeding_type_cues` 隔离。

**Alternatives：** 扩 TYPE——否决（TYPE 已胖；查史策略与类型判定生命周期不同）。

### D2：两维枚举

| 维 | 值 | 含义 |
|----|-----|------|
| `point_pick` | `latest` | 按开始时间取最近一条（有无 end 均参与） |
| `point_pick` | `prefer_completed` | 现逻辑：最近已完成；无已完成则最近进行中 |
| `open_speak` | `elapsed` | 选中行无 end：用 `now−start` 报已持续/已睡约 X |
| `open_speak` | `in_progress` | 选中行无 end：现「正在进行中」口径（可拼 active-eta） |

有 end 的行：仍用既有「用时 end−start」等 typed 点查话术；`open_speak` 仅在选中行为进行中时生效。

示例纠偏：「睡了多久了」→ `latest`+`elapsed`；「上次睡眠多久/上一次」→ 常 `prefer_completed`。

### D3：调用时机与缺维策略

```
speak_history 点查分支（非 daily）
  → 用用户句/段原文查 history_speak 飞轮
  → 命中且两维合法 → 采用
  → 否则 → HISTORY-SPEAK 小 LLM（必调）
  → 合法则可选写 keywords 入飞轮
  → 按两维 _pick / format
```

LLM 失败或仍非法：降级播报「暂时无法准确回答上次情况」类短句，**MUST NOT** 静默套用 `prefer_completed`（产品已否决缺维默认旧逻辑）。

### D4：LLM 契约

提示词常量（如 `HISTORY_SPEAK_LLM_PROMPT`）：只出 JSON：`point_pick`、`open_speak`、`need_confirm`（本变更默认忽略确认、直播）、`keywords[]`。SSE 真流式 + 中文 reasoning。不写 events。

写入：高置信且 keywords 非空则灌库；空 keywords 可回退规范化短句一条（禁止复合整句）。

### D5：选行与话术落地

- 替换/分支 `_pick_completed_or_only_open`：`latest` → `max(rows, key=start_ts)`；`prefer_completed` → 旧逻辑。
- `only_open` 话术：`elapsed` → 新模板（相对开始时间 + 已持续）；`in_progress` → `_format_only_in_progress`（保留 ETA 拼接条件）。
- 父塌缩 / 多叶点查：每事件组各自按同一两维选行。

### D6：Admin

镜像 type-cache：`/v1/admin/history-speak-cache`（list/bulk/dedupe/delete）。Go Hub 兄弟仓页。

### D7：与 ETA / predict

- `open_speak=in_progress` 且走「仅进行中」模板时，保留 `predict-active-timing-eta` 拉 ETA。
- `elapsed` 不强制拉 ETA（可仍拉但不拼进 elapsed 主句，避免两套时间打架；默认不拼）。
- predict「还有多久醒来」不进本飞轮。

## Risks / Trade-offs

- [冷启动每点查一次 LLM] → 飞轮种子「多久了/上次/上一次」；阈值对齐 type cue（可用 0.9）
- [「多久」串 predict] → TYPE 已分轨；本 LLM 仅在已是 history 点查后调用
- [elapsed 时钟漂移] → 用服务端 Asia/Shanghai now
- [LLM 失败无答] → 明确降级句，不回落错误旧策略
- [Hub 未就绪] → Python admin 可先用；种子可脚本/bulk

## Migration Plan

1. 上线 store + LLM + speak_history 接线 + admin。
2. bulk 种子：「多久了」「睡了多久」→ latest+elapsed；「上次」「上一次」→ prefer_completed+in_progress（或 elapsed 按产品微调）。
3. 验收「睡了多久了」+ 进行中睡眠 → 最近开表 + 已持续。
4. 回滚：恢复硬编码 prefer_completed（仅应急）。

## Open Questions

（无；explore 已定：独立飞轮、缺维走 LLM、四值枚举、默认不确认。）
