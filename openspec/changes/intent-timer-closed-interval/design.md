## Context

意图落库：`collect_event_items` → `POST /device/history/api/event/batch`。计时叶子 create 当前一律 `end_time=0`。Go `AddDeviceHistory` 经 `guardDuplicateOpenHistoryStart`：**仅当本次 EndTime==0 且同 event 已有进行中时拒绝**；EndTime>0 始终可插入。槽位覆盖已有 clock；尚无 duration；「≥2 clocks × 单条 events」会强制降级 LLM，误伤「8点到8点半」。

## Goals / Non-Goals

**Goals:**

- 闭合补记三场景：有钟点+时长、无钟点+时长、双钟点起止。
- collect 尊重计时 create 的显式 end_time。
- 起止对不触发多钟点降级；多段喂养（≥3 钟点等）仍可降级。
- 有进行中同叶时，闭合补记可成功。

**Non-Goals:**

- 修改 Go 互斥或 batch 协议。
- 「有进行中再 start 则自动先 end」。
- 把「10分钟」写入 eventNumber（时长只推 end_time）。

## Decisions

### D1：闭合判定优先于开表

对计时叶子 create：

1. 抽到 duration 且有 1 clock → start=clock，end=start+duration  
2. 抽到 duration 且 0 clock → start=now−duration，end=now  
3. 恰好 2 clocks 且像起止（含「到/至/～/-」或仅两钟点单事件）→ start=较早，end=较晚；不降级 LLM  
4. 仅 1 clock、无 duration → 开表 end=0（真开始）  
5. ≥3 clocks 且单条 events → 仍强制 LLM（多段）

### D2：collect 尊重 end_time

```
if create and timer:
  if ev.end_time > 0: use it
  else: end_time = 0  # 开表
```

非计时 create 仍 end=start（瞬时）。

### D3：时长独立抽取，不走毫升 qty

`N分钟` / `N分` → 秒；overlay 只写 start/end，不写 quantity。

### D4：Go 不改

契约仍 batch create；闭合由 Python 填 EndTime>0。

### D5：与 overlay 降级共存

将「多钟点降级」收窄为：非起止对的多钟点（如 ≥3，或 2 钟点但无起止语义且伴多 qty 等）。默认两 clock + 单计时事件按起止处理。

## Risks / Trade-offs

- [「喂了10分钟」误当闭合] → 结合计时叶子与「分钟」单位；开表话术仍无时长则 end=0。  
- [两 clock 非起止] → 有「到/至」优先；否则单事件两 clock 按起止，多段靠 ≥3 或 LLM。  
- [跨日 23 点到 1 点] → 一期按同日排序；跨日可后续。

## Migration Plan

仅 Python 发布；无需数据迁移。回滚：恢复 collect 强制 end=0 与旧降级即可。

## Open Questions

- 无（实现默认：两 clock + 单条计时 create 即起止；有「到/至/～」更强信号）。
