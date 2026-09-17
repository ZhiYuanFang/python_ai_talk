## ADDED Requirements

### Requirement: No care-alert prompt-flywheel env knobs required for product loop

环境配置 MAY 保留 `CARE_ALERT_PROMPT_DIR` 供静态 `prompt.json` 加载。系统 MUST NOT 将 care_alert 反馈飞轮重写频率、ledger 路径等作为产品闭环的必需配置；删除飞轮后相关可选 knobs MAY 从 settings / `.env.example` 移除。

#### Scenario: Analyze works with static prompt dir only

- **WHEN** 配置了可读的 care_alert prompt 目录且其中有有效静态模板
- **THEN** analyze 可运行且不依赖飞轮重写相关环境变量
