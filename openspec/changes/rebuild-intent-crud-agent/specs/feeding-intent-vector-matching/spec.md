## REMOVED Requirements

### Requirement: 系统使用向量相似度进行喂养事件匹配
**Reason**: 事件名 Top-1 把整句压成单个 `event_id`，与多事件 CRUD 意图缓存冲突；分类提示已含事件字典，不再需要第二套向量身份。
**Migration**: 缓存 miss 走 `classify_intent`；重复句走 `feeding_intents`。删除 `match_event_by_vector`。

### Requirement: 向量匹配结果包含置信度信息
**Reason**: 事件名向量匹配已删除。
**Migration**: 意图缓存可自带相似度；分类结果不依赖事件名向量分数。

### Requirement: 向量匹配支持多个结果返回
**Reason**: 事件名向量匹配已删除。
**Migration**: 无。

## ADDED Requirements

### Requirement: 意图路径不得做事件名向量匹配
意图分析图 MUST NOT 注册或调用 `match_event_by_vector`。系统 MUST NOT 再用 `feeding_events`（或等价事件名向量库）对用户输入做 Top-1 事件名相似度匹配，并据此直接定为 feeding create、跳过分类或免确认。冷启动未见过的句子 SHALL 进入分类 LLM（可先做备注探针）。知识库向量检索 MUST NOT 随本条删除。

#### Scenario: 首次记事件走分类
- **WHEN** 用户输入「开始睡眠」且意图缓存未命中
- **THEN** 系统 SHALL 进入 `classify_intent`（或确认 pending）
- **AND** SHALL NOT 因标准事件名向量高分直接 END 并落库

#### Scenario: 复合句不会被事件名短路
- **WHEN** 用户输入「吃完奶，换了尿布」且意图缓存未命中
- **THEN** 系统 SHALL 进入分类以保留多事件可能
- **AND** SHALL NOT 存在事件名向量节点将其压成单事件 create

#### Scenario: 查询句不会被事件名落 feeding
- **WHEN** 用户输入「上一次拉屎是什么时候」
- **THEN** 系统 SHALL 经分类或缓存得到 `op=read`（或等价查记录）
- **AND** SHALL NOT 经事件名向量定为 feeding create
