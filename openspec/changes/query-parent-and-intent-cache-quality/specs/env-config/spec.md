## ADDED Requirements

### Requirement: 启动可一次性清空意图缓存
系统 SHALL 提供环境变量 `CLEAR_FEEDING_INTENTS_ON_STARTUP`（默认 `false`），三层同名：`.env` 文件、docker-compose 注入、`settings.py` 读取。为 true 时服务启动预热 MUST 删除并重建空的 `feeding_intents` Collection，MUST NOT 删除 `mother_baby_knowledge`。默认 false 时 MUST NOT 因启动而清空意图缓存。

#### Scenario: Clear disabled by default
- **WHEN** 未设置该变量或值为 false
- **THEN** 启动预热 SHALL NOT 删除 `feeding_intents` 中已有条目

#### Scenario: Clear enabled wipes only intent cache
- **WHEN** `CLEAR_FEEDING_INTENTS_ON_STARTUP=true` 且服务完成向量预热
- **THEN** 系统 SHALL 清空 `feeding_intents`
- **AND** SHALL NOT 清空 `mother_baby_knowledge`

#### Scenario: Three-layer same name
- **WHEN** 在 env/.env.prod 中定义 `CLEAR_FEEDING_INTENTS_ON_STARTUP=false`
- **THEN** docker-compose.yml 的 environment 段 SHALL 注入同名变量
- **AND** python `settings` SHALL 读取到对应布尔值

### Requirement: 移除退役的标准事件向量重建开关
环境文件、docker-compose、settings 与 `docs/deploy-guide.md` MUST NOT 再声明或文档化 `REBUILD_FEEDING_STANDARD_EVENTS`。

#### Scenario: Prod env has no dead rebuild flag
- **WHEN** 运维查看 env/.env.prod 与 deploy-guide 环境变量表
- **THEN** SHALL NOT 出现 `REBUILD_FEEDING_STANDARD_EVENTS`
