## REMOVED Requirements

### Requirement: 类型关键字飞轮驱动 target_type
**Reason**：顶层改为 C/R/U/D/exit/other；短关键词 TYPE 飞轮（feeding_type_cues 承载 feeding/history/predict）易串「多久」且与整段飞轮策略冲突。  
**Migration**：新建/改用 OP 整段飞轮（见 `intent-flywheel-layers`）；停用短关键词 TYPE 热路径；存量 `feeding_type_cues` 清空或只读迁移后删除热路径依赖。

## ADDED Requirements

### Requirement: OP 整段飞轮替代 TYPE 短词飞轮
系统 SHALL 使用整段原文飞轮判定 `create|read|update|delete|exit|other`。热路径命中合法 OP 时 MUST 跳过 OP 分类小 LLM。系统 MUST NOT 继续以短关键词 TYPE 飞轮作为主分类加速手段。

#### Scenario: 整段命中 read
- **WHEN** 段「睡了多久了」命中 OP 飞轮且 payload 为 read
- **THEN** 系统 SHALL 采用 read 轨且 MUST NOT 再走短关键词 TYPE 飞轮主路径
