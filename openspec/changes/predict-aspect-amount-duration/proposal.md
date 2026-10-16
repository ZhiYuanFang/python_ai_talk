## Why

「这次配方奶要吃多少」被顶层轨判成预测后，只能落进「下一次 + 几点」。没把握时确认句固定成「大概还要多久」，图在确认处结束，进不了预测播报。预测目前只有「何时」两格（进行中/下一次 × 几点/还要多久），用量和用时没有自己的格子。

## What Changes

- 预测增加第三维 `predict_aspect`：`when` | `amount` | `duration`（何时 / 用量 / 用时）。`time_answer` 只在 `when` 时填写 `clock` | `remain`。
- 问用量或用时时跳过 Go 时间点热路径，用冷路径里的预计用量或预计用时作答；两个数都保留，由这一格决定念哪一个。
- 没把握时的确认句跟着这一格走：用量问「要吃多少」，用时问「大概要持续多久」，何时才问「还要多久」或「大概几点」。
- 「上次 / 上一次」的吃了多少、睡了多久仍走查记录，不因新格子进入预测。
- 旧预测飞轮没有 `predict_aspect` 时按 `when` 读。

## Capabilities

### New Capabilities

- `predict-ask-aspect`：预测第三维用量/用时的判定、确认话术、热路径让路，以及算法同时保留预计用量与预计用时

### Modified Capabilities

- `intent-predict-qa`：`when` 仍走现有 clock/remain 热路径模板；`amount` / `duration` 不得被「下次几点」模板截走

## Impact

- 本仓：顶层轨与预测两维提示词、`predict_aspect` 字段与飞轮载荷、确认话术、`speak_predict` 热/冷路径分流、本地预测算法不再二选一丢掉另一个数
- 不改查记录的「上一次用时」模板；不新增测试文件
