## Context

现网 R·predict：`speak_predict` 按 `predict_channel` 拉 Go active-eta / imminent，命中则模板 clock/remain；无数据则「暂时估不准」，禁止回落查史用时。算法在 Flutter（`event_next_predictor` + 近 7 日史 + 预约旁路），结果同步 Redis；预约 `appointment/next` **不**写入 predict Redis。Python 已用 Redis（LLM 闸门、clinic companion），可复用客户端新前缀做算法快照。共享紧凑史：`build_feeding_history_prompt_blocks`（窗由调用方定）。

## Goals / Non-Goals

**Goals:**

- Go 命中保留模板；miss / 预约走本地算法或约定 + 语境史 + LLM 终答。
- 算法对齐 Flutter：非预约近 7 日加权中位间隔与 expect 用量/时长；预约用约定 nextAt。
- 语境 TIME 与查史同方法，只决定 LLM 史窗；算法窗固定 7 日。
- Redis 算法快照 TTL 10min；CUD 落库成功清快照。
- 样本不足 / 无预约约定明确降级，禁止 LLM 编造数字。

**Non-Goals:**

- 改 Flutter 算法源；回写 Go imminent；Go 命中改走 LLM。
- 多事件比较 / TOD 分桶间隔暴露（可二期）；回忆种子旁路首版可不做。
- 新建测试文件；把算法结果写入意图/时间分类飞轮。

## Decisions

### D1：双轨输入，单次 LLM 终答（语境史按需）

```
Go miss / 预约
  ├─ 算法轨：固定 7 日工具 或 appointment/next（始终）
  └─ 语境轨（按需）：日词/近况/规律线索 → TIME 同方法 → 拉史 → compact
       → LLM(原话 + 工具 JSON [+ history_text])
```

纯「下次何时 / 还有多久」：**不拉语境史**，只灌原话+工具。  
有「最近/这周/隔多久/比上次」等才拉史。  

**Alternatives：** 凡兜底都默认 7 日语境史——否决（纯 next 浪费且噪声）。语境窗驱动算法——否决（与 Flutter 7 日不一致）。

### D2：算法封装范围

Python `feeding` 内移植场景核：occurrence 序列 → TOD+半衰期加权中位间隔 → nextAt；expect duration/amount 胜出；`catalogRootIsAppointment` 旁路。月龄半衰期若缺 birthDate 用 Flutter 默认档。不移植 UI/小组件/回忆 onboarding。

### D3：预约

对齐 Go：`event.is_appointment` → JSON `isAppointment`，**仅看命中事件自身**（默认 0；与 eventType 正交）。禁止「根或子树任一为真则整根预约」聚合。孪生 internal GET 对齐 App `GET .../appointment/next`（deviceNo+**该 eventId** → nextAt）。无约定或过期：明确降级文案，不跑间隔算法冒充。

### D4：Redis 快照

- Key：`predict_algo:{device_no}`（或等价前缀），与 `llm_gate` / companion 隔离。
- Value：按 root 的工具/约定快照 JSON（interval/nextAt/expect…）。
- TTL：600s；CUD（create/update/delete/改史 end）落库成功 `DEL`。
- 命中：跳过 7 日重拉与重算（预约项可一并缓存）；终答仍 LLM；remain 用 nextAt−now 现算。
- App 改史/改约本仓不知：靠 TTL。

**Alternatives：** 仅进程内存——否决（多 worker 重复算）。回写 imminent——否决（预约本就不进 Redis；写主权复杂）。

### D5：TIME 与段流水线

查史继续现有 TIME。预测 **Go 命中** 可不跑 TIME。**兜底** 仅在语境史闸门命中时用同一 `resolve_time` / 日词 / 飞轮解窗拉语境史；已触发拉史但无更尖日词时窗默认近 7 日。禁止为预测另写第三套 TIME；禁止无线索时默认灌 7 日语境史。

### D6：提示词与流式

兜底 system 落 `feeding/.../prompts/system.py`；约束只能依据注入的史与工具数字作答，禁止编造；reasoning 中文；意图 SSE 路径 `stream(thinking_enabled=True)`。

## Risks / Trade-offs

- [App 改史后 10min 内旧快照] → TTL + CUD 主动清；可接受。
- [无 birthDate 半衰期偏差] → 默认档；有画像再精化。
- [语境窗 ≫ 7 日两次拉史] → 可优化为一次大窗切片；首版正确优先。
- [孪生无 appointment internal] → 兜底预约全降级；Go 同发或先发。
- [project.md「勿直连 Redis」字面] → 与闸门/companion 既有实践一致：仅本仓会话/闸门/本快照键，不直连业务 DB 或 Go predict 键。

## Migration Plan

1. Go：appointment next internal GET + 密钥中间件。
2. Python：工具模块 → Redis 快照 → speak_predict 分支 → CUD 清钥 → 提示词。
3. 回滚：关掉兜底分支即回「估不准」；删 Redis 前缀无破坏。

## Open Questions

（无；探索已敲定：Go 模板保留、7 日算法窗、语境 TIME 仅 LLM 史、Redis TTL 10min+CUD 清、补预约。）
