## ADDED Requirements

### Requirement: 规则缺口须落在 Chroma 持久目录内
系统 SHALL 将规则缺口收件箱持久化为 JSONL（或等价文件），路径 MUST 位于配置的 Chroma 持久化目录之下（如 `{CHROMA_PERSIST_DIR}/rule_gaps/gaps.jsonl`）。系统 MUST NOT 将权威缺口文件写到该持久目录的父级兄弟路径（如 `chroma_db/../rule_gaps`），以免脱离既有 Docker chroma 卷而导致容器重建丢数据。

#### Scenario: 文件在 chroma 卷内
- **WHEN** 服务写入一条规则缺口且 `CHROMA_PERSIST_DIR` 指向已挂载的 chroma 数据目录
- **THEN** 缺口文件路径 SHALL 以该目录为前缀（含子目录 `rule_gaps`）
- **AND** MUST NOT 仅依赖未挂载的容器可写层作为权威存储

### Requirement: open 缺口须稳留至人工处理
系统 MUST NOT 因进程重启、服务重启或容器重建（在 chroma 持久卷保留的前提下）删除、截断或清空 `status=open` 的规则缺口记录。系统 MUST NOT 因 `CLEAR_FEEDING_INTENTS_ON_STARTUP`（或等价意图集合清空开关）改动规则缺口文件。仅当管理端将记录标为已处理（如 `dismissed`）或显式删除时，该条方可从默认 open 列表消失。

#### Scenario: 重建容器后 open 仍在
- **WHEN** 已有 open 缺口落在 chroma 持久卷内，且运维重建容器但保留该卷
- **THEN** 管理端默认 open 列表 SHALL 仍能读到这些记录

#### Scenario: 清意图库不影响缺口
- **WHEN** 启动时 `CLEAR_FEEDING_INTENTS_ON_STARTUP=true` 清空 `feeding_intents`
- **THEN** 系统 SHALL NOT 因此删除或清空规则缺口 JSONL

### Requirement: 旧路径一次性迁移
当新路径（chroma 目录内）尚无有效缺口文件，且旧路径 `CHROMA_PERSIST_DIR/../rule_gaps/gaps.jsonl`（或等价兄弟路径）存在可读内容时，系统 SHALL 在初始化缺口存储时将该文件一次性迁移到新路径。迁移失败 MUST NOT 阻断服务启动；MUST 记录日志。若新路径已有内容，系统 MUST NOT 用旧文件覆盖新文件。

#### Scenario: 升级迁入旧箱
- **WHEN** 旧路径存在非空 `gaps.jsonl` 且新路径不存在或为空
- **THEN** 系统 SHALL 将内容迁至新路径，使后续列表可读到原记录
