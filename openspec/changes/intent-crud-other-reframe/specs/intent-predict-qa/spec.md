## ADDED Requirements

### Requirement: 预测问答收归 read 轨
预测类问答（进行中 ETA、下次 imminent）MUST 在顶层意图轨为 `read` 时，经 R 内 `source=predict` 处理。系统 MUST NOT 再将 `predict` 作为与 create/read 平级的顶层 `target_type`。`predict_channel`（active|next）与 `time_answer`（clock|remain）MUST 仍分维存储，仅在 source=predict 时有效。

#### Scenario: 还有多久醒来
- **WHEN** 用户说「大概还有多久醒来」且判为 read + source=predict
- **THEN** predict_channel SHALL 为 active，time_answer SHALL 为 remain
- **AND** 系统 MUST NOT 以顶层 history/predict 枚举互抢主轨

## REMOVED Requirements

### Requirement: Intent SHALL support target_type predict with separate channel and time_answer
**Reason**：预测不再作为顶层 target_type；改由 read 轨内 source=predict 承载。  
**Migration**：TYPE/飞轮与图路由改为 OP=read + R·predict 子维；清理顶层 predict 枚举与「合法 predict 压查史」门闩。
