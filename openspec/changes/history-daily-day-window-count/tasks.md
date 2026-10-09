## 1. daily 日词补窗

- [x] 1.1 实现原文→今天/昨天/前天（及约定本周）→ unix 窗，复用或扩展 `enum_to_unix`（中文注释）
- [x] 1.2 `speak_history`（确认后同一拉史路径）：daily + 窗无效 + 非 ignore 时写入补窗后再 filter
- [x] 1.3 「和昨天比」等对比问避免误收成单日昨天窗（设计 D2/风险表）

## 2. 次数播报

- [x] 2.1 次数问线索检测（可复用 `history_mode_cues`/几次词表）
- [x] 2.2 daily + 次数问：content 显式含 N 次；number 叶不得只报总量
- [x] 2.3 非次数 daily 保持现有紧凑流水/Δ 行为

## 3. 验收对照

- [x] 3.1 手工：「昨天喝了几次水」→ filter 带昨天窗，content 含次数（补窗+次数句已通；请本地点验）
- [x] 3.2 手工：已有有效窗的 daily 不被日词覆盖（仅 start/end 均无效时补）
