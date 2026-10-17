## Why

「上一次配方奶是什么时候」在意图已经判成点查之后，仍会调用查史播报策略模型，只为选出提示词里已经写死的两个标签。父事件点查（如「上一次喂养是什么时候」）还会再问一次模型去猜叶子，而最近一条历史记录的开始时间就能决定是哪个子事件。

## What Changes

- 点查播报在飞轮与小模型之前走本地规则。含「上次 / 上一次 / 最近一次」时为优先已完成、进行中只说正在进行；含「多久了 / 多长时间了」且不含上述词时为最近一条、进行中报已持续多久。命中则不再查飞轮、不调播报模型。
- 父事件点查不再把猜叶子交给模型。取该父下全部可落库子孙叶子，按每个叶子最近一条记录的开始时间选出最晚的叶子作为本轮事件。
- 这些叶子在历史里一条记录都没有时，打断并短问子事件名，不继续播报、不调用猜叶子模型。
- 事件未识别、多候选消歧仍走原有猜测路径。

## Capabilities

### New Capabilities

- `point-speak-local-rules`: 点查播报策略在飞轮与小模型之前由本地规则决定选行与进行中话术
- `parent-point-leaf-by-time`: 父事件点查按各子事件最近记录的开始时间选定叶子，无记录则短问事件名

### Modified Capabilities

- （无）当前基线 `openspec/specs/v0.0.1.md` 未收录点查播报的规则顺序，也未要求父事件点查用开始时间选叶子。

## Impact

- `app/feeding/services/history_speak_policy.py`、`app/feeding/services/dim_local_rules.py`（或同等本地规则入口）
- `app/feeding/services/history_event_guess.py`、`app/feeding/services/segment_multidim.py` 中父事件点查分支
- 确认追问沿用现有 `need_confirm` 路径，问句只列子事件名
