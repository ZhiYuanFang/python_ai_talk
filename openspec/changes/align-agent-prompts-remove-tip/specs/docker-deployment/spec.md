## ADDED Requirements

### Requirement: Care-alert prompt volume not required

部署 MUST NOT 再将 care_alert 数据目录挂载列为加载 system 提示词的必达项（system 已内联）。Chroma 意图缓存卷约定保持独立。

#### Scenario: Start without care_alert prompt file

- **WHEN** 容器未挂载或缺少 `data/care_alert/prompt.json`
- **THEN** care_alert analyze MUST 仍可使用内联 system 提示词运行
