## ADDED Requirements

### Requirement: Care-alert prompt dir env optional or removed

`CARE_ALERT_PROMPT_DIR`（或等价）MUST NOT 再作为加载 care_alert system 提示词的必需配置。实现 MAY 从 settings 删除该字段。

#### Scenario: Analyze without CARE_ALERT_PROMPT_DIR

- **WHEN** 环境未设置 care_alert prompt 目录
- **THEN** care_alert 仍使用代码内 `system.py` 常量构建 system 提示词
