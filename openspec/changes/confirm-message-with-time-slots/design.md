## Context

- 单事件：`build_leaf_confirm_message(name, action)` →「您是要记录「X」吗？」；`create_leaf_confirm_pending` 主路径常不传 `start_time`/`end_time`。
- 多事件：`build_multi_event_confirm_message` 已带「量 +（今天 HH:MM）」，日段粗、无区间 end、语序不够口语。
- 产品拍板：日段从将落库的 unix **反推**（贴合落库）；无有效时间一律加「现在」；查/删话术不动。

## Goals / Non-Goals

**Goals:**

- 记录类（create / start / end）确认单句与多句共用槽位格式化。
- 反推：今天/昨天/前天/更早日期 + 日段（凌晨/早上/上午/中午/下午/晚上等）+ 钟点。
- 无时间 →「现在」；区间 end>start →「A 到 B」；有 quantity 时自然嵌入。
- pipeline 把子项时间/数量传入 pending 与话术。

**Non-Goals:**

- 不改查记录 / 删除确认句式。
- 不解析用户原话日段词做确认文案。
- 不改落库时间计算本身（只读已有槽位）。
- 不新增测试文件。

## Decisions

### D1：`format_confirm_slot(ev, *, now)` 单一出口

输入子项 dict（至少 name、op/action、quantity、start_time、end_time），返回不含「您是要…吗？」外壳的动词短语片段。

模式优先级：

1. **区间**：有效 start 且 end>start →「记录{日段时点}到{时点}的「名」」（同日可省略第二段日；跨日第二段带日）
2. **开表**：action/op 为 start，或 create+start 且无有效 end →「{时间}开始「名」」；无时间 →「现在开始「名」」
3. **结束**：op/action 为 end →「{时间}结束「名」」；无时间 →「现在结束「名」」
4. **瞬时记录**：其余 create/one →「记录{时间短语}的「名」」或带量「记录{时间}吃了 N 毫升「名」」；无时间 →「现在记录「名」」（有量则「现在记录 N 毫升「名」」）

整句：`您是要{片段}吗？`；多事件用「并」/顿号规则同现实现。

### D2：日段反推表（Asia/Shanghai）

相对 `now`：

- 同日 → 不说「今天」或可省略日词，保留日段+钟点（实现选：有日段则「早上 8 点」，无则「今天 8 点」）
- 昨天 →「昨晚」若小时在晚间段，否则「昨天早上/上午…」
- 前天及更早 →「前天…」或「M月D日…」

小时粗分（可微调）：0–5 凌晨，5–9 早上，9–12 上午，12–14 中午，14–18 下午，18–24 晚上。

钟点口语：整点「6 点」；有分「6 点 30 分」或「6:30」（实现统一一种）。

### D3：「现在」判定

- `start_time` 空 / 0 / 不可解析 → 无时间 →「现在」
- 可选：`|start - now| < 120s` 也视为「现在」，避免刚分类写入的「此刻」念成精确 HH:mm——**采用 120 秒阈值**。

开表有 start=现在减 0、end=0：有有效 start 时按阈值走「现在开始」或「HH:mm 开始」，**不要**因 end=0 误判无时间。

### D4：管道补传

`intent_pipeline` 叶子 `create_leaf_confirm_pending` 传入：

- `start_time` / `end_time` / `quantity` 来自 `head` 或 `events[0]`
- 默认话术改为调用带槽位的 leaf builder（或从单元素 events 走 `format_confirm_slot`）
- 显式 `confirm_message` 覆盖仍优先

多事件继续覆盖 `clarify_message = build_multi_event_confirm_message(events)`，内部改用 `format_confirm_slot`。

### D5：查/删不动

`build_history_confirm_message` / `build_delete_confirm_message` 保持现状。

## Risks / Trade-offs

- **[日段边界主观]** 18 点算晚上 vs 傍晚 → Mitigation：表写入 design/注释，可后调。
- **[有量动词「吃了」]** 仅对带 quantity 的数量型事件自然；其它单位仍说「记录 N…」→ Mitigation：默认「N 毫升」与现多事件一致；无单位信息时「N」。
- **[超长多事件句]** → Mitigation：保持现拼接；不截断。

## Migration Plan

直接上线；回滚恢复旧 builder。无数据迁移。

## Open Questions

（无阻塞；「吃了」是否仅配方奶/母乳等可在实现时用 event 名启发式，失败则退回「记录」。）
