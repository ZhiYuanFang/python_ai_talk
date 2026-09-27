## MODIFIED Requirements

### Requirement: History events in prompts are field-trimmed

向 LLM 注入喂养历史时，系统 SHALL 采用下列之一：（1）共享紧凑聚合文本（日历日 × 事件名·时刻与总量，史行不含 eventId）；或（2）仅保留 eventName、eventNumber、startTime、endTime、remark 等约定字段的裁剪列表（缺失则省略）。clinic 在 `needs_history` 为真时的主喂养史块 SHALL 使用共享紧凑聚合文本。SHALL NOT 把无关元数据整包塞入查记录/clinic 提示；SHALL NOT 再使用已删除的薄按日汇总函数作为 clinic 注入形态。

#### Scenario: Clinic needs-history uses shared compact

- **WHEN** clinic_answer（或共用注入）在 needs_history 为真时格式化喂养史
- **THEN** 主喂养史块为共享紧凑聚合文本
- **AND** MUST NOT 依赖 `build_daily_history_summary`

#### Scenario: Trimmed history JSON still allowed on other paths

- **WHEN** 非 clinic 主归纳路径仍使用字段裁剪列表注入
- **THEN** 每条记录仅含约定字段子集
