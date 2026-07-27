## Why

喂养落库必须精确到叶子事件，父事件不可记。命中父类时必须列出子类消歧。现有确认流假定 `/intent/confirm` + `confirm|reject`，与真实交互严重错位：用户在同一输入框**打字回应提问，任意内容都可能出现**。新功能研发中不保留旧提问/确认通道，按自由文本续聊实现。

## What Changes

- **BREAKING**：废除以 `confirm|reject` 枚举为主的提问恢复路径（含 `/intent/confirm` 及相关节点）；主路径改为同一 `/intent` 输入框 + 可选 `conversation_id`
- 事件字典保留全量树；匹配与落库仅使用叶子视图；有子节点的父事件不得作为最终 `event_id`
- 名称 / 向量 / LLM 任一命中父事件时强制消歧：返回子选项与问句，写入 pending
- pending 下解析**任意自由文本**：唯一子命中则落叶子；模糊再问；拒绝词清 pending；**其余一律视为答非所问，清 pending 并将本句当新意图重跑**（不设合法回复白名单）
- 飞轮仅在消歧成功落到唯一叶子后，将消歧前用户原话写入该叶子；短回复与父事件永不入飞轮
- 保持事件字典 24 小时 TTL 拉取与增量同步；同步移除父类标准向量且不删 `source=user`

## Capabilities

### New Capabilities

- `parent-event-disambiguation`: 父不可落库；命中父强制消歧；同一 `/intent` + 自由文本 pending；任意离题回复当新意图
- `leaf-only-event-dictionary`: 全量树与叶子视图分离；对外匹配/落库仅叶子；24h 刷新保持不变量

### Modified Capabilities

- （无：`openspec/specs/` 尚无已归档对应能力；旧 confirm 枚举契约直接替换）

## Impact

- 代码：`event_cache`（全量+叶子）、`event_hierarchy` / `clarification` / `intent_pipeline`、意图路由与图、schema（`conversation_id` / `options` / `confirm_type`）、删除旧 confirm 主路径
- **BREAKING**：客户端须用同一输入框带 `conversation_id` 打字续聊，不再依赖 confirm 枚举接口
- 向量库：父类标准条目移除或禁止可落库命中；飞轮只写叶子
- 24h 刷新与飞轮闭环保持有效
