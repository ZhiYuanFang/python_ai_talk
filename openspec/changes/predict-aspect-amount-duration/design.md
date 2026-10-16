## Context

预测现在只有两维：`predict_channel`（`active`|`next`）和 `time_answer`（`clock`|`remain`）。两维都在回答「何时」。热路径只要对上 `expectEndAt` 或 `nextAt`，就用模板念几点或还要多久。

「这次配方奶要吃多少」被顶层轨小模型判成 `read` + `predict` + `next` + `clock`，并标 `need_confirm`。拼装时预测轨的确认句不看原话，固定为「大概还要多久」。图在确认处结束，进不了 `speak_predict`。

冷路径算法已经会算预计用量和预计用时，但两边都有数时只留一个（计时类留用时，数量类留用量）。兜底模型因此经常看不到被丢掉的那一个数。

## Goals / Non-Goals

**Goals:**

- 增加 `predict_aspect`：`when` | `amount` | `duration`。
- 问用量或用时时跳过时间点热路径，用预计用量或预计用时回答。
- 两个预计数都保留，由这一格选择念哪一个。
- 确认句跟着这一格走。
- 旧飞轮无此字段时按 `when` 读。

**Non-Goals:**

- 不把「上次 / 上一次」的吃了多少、睡了多久改成预测。
- 不把 `time_answer` 扩成用量/用时。
- 不改查记录点查模板。
- 不问「瓶子里还剩多少」；预计用量是历史中位，不是当前剩余。

## Decisions

### D1. 第三维独立字段

字段名 `predict_aspect`。`when` 继续要求 `time_answer` 为 `clock` 或 `remain`。`amount` 与 `duration` 的 `time_answer` 必须为空。`predict_channel` 三种问法都要有：`active` 表示进行中这一次，`next` 表示即将这一次（含「这次要吃多少」）。

不把用量/用时塞进 `time_answer`。那一维只描述怎么念一个时间点，和「吃多少」不是同一种答法。

### D2. 合法才算填满

预测轨填满的条件：

- `predict_channel` 为 `active` 或 `next`
- `predict_aspect` 为 `when` 且 `time_answer` 为 `clock` 或 `remain`
- 或 `predict_aspect` 为 `amount` 或 `duration` 且 `time_answer` 为空

缺格或非法组合仍 `need_confirm`，不执行。旧飞轮载荷没有 `predict_aspect` 时视为 `when`，原有 `time_answer` 继续有效。

### D3. 热路径只服务「何时」

`speak_predict` 仅在 `predict_aspect` 为 `when`（或旧数据缺省为 `when`）时走 Go 锚点模板。`amount` / `duration` 即使 imminent 里有 `nextAt` 也进入冷路径。否则「下次几点」模板会把用量题截走。

### D4. 算法两个数都留

本地预测工具在样本够时同时写出 `expect_amount` 与 `expect_duration_sec`，不再二选一后丢掉另一个。播报按 `predict_aspect` 取数：问用量只用用量，问用时只用用时。所问的数没有时，说明这个数估不出，不得改念另一个数，也不得改念「上一次用时」。

冷路径终答仍走现有预测兜底模型（原话 + 工具 JSON）。提示词写明本轮只回答用量或用时，禁止改答成几点。样本不足沿用「数据量太少，无法预测」。

### D5. 确认句按格子

没把握且预测轨已有事件名时：

- `when` + `remain`：大概还要多久
- `when` + `clock`：大概几点
- `amount`：要吃（或用）多少
- `duration`：大概要持续多久

`need_confirm` 为真时仍不执行、不写飞轮。格子合法且模型标了有把握时直接播报。

### D6. 提示词把用量/用时从「何时」里分开

顶层轨与预测维提示词增加例子：

- 「这次要吃多少 / 大概要喝多少」→ `predict` + `next` + `amount`
- 「这次要吃多久 / 大概要睡多久」→ `predict` + `next` + `duration`
- 「还有多久喂 / 几点醒」→ `predict` + `when` + 原有 channel / time_answer
- 「上次吃了多少 / 睡了多久」→ `read` + `record`

飞轮载荷增加 `predict_aspect`。回写条件不变：没把握不写。

## Risks / Trade-offs

- [进行中 + 用量被理解成「还剩多少」] → 文案与提示词写预计这一次的用量，不写剩余。
- [模型仍把用量题标没把握] → 确认句至少问「要吃多少」，不再问「还要多久」。
- [旧飞轮缺字段] → 读取时缺省 `when`，已记住的「几点醒」不被改成用量。
- [两个数都算略增冷路径开销] → 只在已进入冷路径时多留一个中位数，热路径的何时题不额外拉史。

## Migration Plan

先读后写：旧 `feeding_predict_cues` 无 `predict_aspect` 的命中按 `when`。新写入带上该字段。无需清库。回滚时忽略未知字段，热路径恢复为只看 channel 与 time_answer。

## Open Questions

无。进行中的用量按「这一次的预计用量」而不是剩余量。
