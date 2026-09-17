## ADDED Requirements

### Requirement: Care-alert volume only for static prompt if retained

若部署仍挂载 care_alert 数据目录，该卷 SHALL 仅需承载静态 prompt（及非飞轮运行文件）；MUST NOT 再将 ledger / 对比样例飞轮持久化列为部署必达项。通识知识 MD 构建与 `mother_baby_knowledge` bootstrap MUST NOT 再作为容器启动必达步骤。

#### Scenario: Deploy without knowledge bootstrap

- **WHEN** 按当前 compose 启动 Python 服务
- **THEN** 启动 MUST NOT 因缺少 `data/knowledge` 或 `build_vector_db` 失败

#### Scenario: Intent cache cleanup remains

- **WHEN** 后台定时清理运行
- **THEN** MAY 清理低质量 `feeding_intents`；MUST NOT 要求清理通识知识集合
