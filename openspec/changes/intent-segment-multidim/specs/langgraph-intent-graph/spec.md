## ADDED Requirements

### Requirement: 意图主图以分句多维替代整包缓存与满血分类
意图分析主路径 SHALL 以「单事件多维 / 复合分句 + 段多维拼装」为编排核心，随后进入既有确认、批量落库或模板查史。系统 MUST NOT 再以「整句意图缓存命中 → overlay_slots → 免确认执行」作为默认热路径，MUST NOT 再以满血一次多 events 分类节点作为默认冷路径。

#### Scenario: 单事件不经整包缓存免确认
- **WHEN** 用户输入单事件短句且事件短说法库命中
- **THEN** 系统 SHALL 经段多维得到事件身份并进入确认或既定执行策略
- **AND** SHALL NOT 直接回放历史整包 multi-events 且 `need_confirm=false` 落库

#### Scenario: 复合句经分句节点
- **WHEN** 用户输入复合句
- **THEN** 图或等价管线 SHALL 包含分句步骤与段循环多维步骤
- **AND** SHALL NOT 跳过段循环而一次产出未经拼装校验的满血 events

### Requirement: 拼装后复用执行与查史节点
段多维拼装得到的 `events[]`（及 target_type / history_mode）SHALL 继续由既有 `execute_history_crud` / `speak_history`（或等价）执行；查史与 CRUD 的 HTTP 边界不变。

#### Scenario: 拼装后 create 走批量落库
- **WHEN** 拼装结果为 feeding create 叶子且已通过确认策略
- **THEN** 系统 SHALL 走批量历史写入路径并模板回执
