## ADDED Requirements

### Requirement: No tip stream in unified stream docs

统一流式编排约定 MUST NOT 再要求实现或保留 `tip_graph` / `/v1/tip/stream` 作为存活能力。clinic、intent、care-alert、growth-trajectory 等存活流式入口仍须遵守 custom thinking + 对外 LLM stream 约定。

#### Scenario: Tip graph not required

- **WHEN** 对照统一流式能力要求
- **THEN** MUST NOT 将 tip_graph 列为必须部署的图入口
