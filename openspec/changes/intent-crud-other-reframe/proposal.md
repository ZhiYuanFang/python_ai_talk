## Why

顶层 `target_type`（feeding/history/predict/conversation）与「对数据做什么」不对齐，「多久」类在 history↔predict 间易串；conversation 口袋过大。需改为按 **C/R/U/D + exit/other** 分轨，并以整段飞轮堆数据，逐步实现热路径少/无 LLM。

## What Changes

- **BREAKING（顶层枚举）**：意图轨改为 `create|read|update|delete|exit|other`（对应 C/R/U/D）。废除作为主轨的 `feeding`/`history`/`predict`/`conversation`/`suggest`（对外与 TYPE 契约）。
- **other**：非喂养 CRUD/exit → 回应「暂不支持」，**不**结束会话；**exit** 仍为退出。
- 复合句拆段后**逐段**走 CRUD；段失败/追问不阻断其它段；**整轮结束后统一汇总**结果与待补信息。
- **end（如睡醒了）** 归 **U**：定窗查史找「仅 start 无 end」；无则 **转 C**。转 C 后按叶子 `one|number|time` 决定 create 形态；`time` 无闭合起止 → 追问。
- **R**：内部再分 `record|predict`（整段飞轮）；record 查史+报点/报段；predict 走 active-eta / imminent（沿用现接口）。
- **一期写库**：Python 按 C/R/U/D 分轨编排；底层 **仍调** Go `event/batch`。Go 分 API 列为二期 Non-Goal。
- **飞轮（整段 document，宁可不中不可错中）**：OP、事件、数量、R·source、R·record 播报、R·predict、U/D 定位策略。
- **时间**：**不做**时间向量飞轮；规则 → TIME LLM → **rule_gap**；缺槽追问。
- **数量**：规则可先试；miss → 快 QTY LLM → **数量飞轮**回写；无量线索仍追问、不写飞轮。

## Capabilities

### New Capabilities

- `intent-crud-rails`：顶层 C/R/U/D/exit/other、段循环与统一汇总、U·end→C、other 话术
- `intent-flywheel-layers`：分层整段飞轮清单；时间禁飞轮；数量飞轮；热路径少 LLM 目标

### Modified Capabilities

- `intent-predict-qa`：预测不再作为顶层 type，收进 R·predict
- `intent-history-query` / `intent-history-speak-flywheel`：收进 R·record（选行/播报服从整段飞轮）
- `intent-type-keyword-flywheel`：**迁移/废止**短关键词 TYPE 飞轮为主轨，改 OP 整段飞轮
- `intent-rule-gap-inbox`：时间维继续缺口；数量可以飞轮为主、缺口可选保留

## Impact

- Python：`TargetType`/`op` 契约、`resolve_type`→OP 分轨、intent 图路由、`speak_history`/`speak_predict` 收束到 R、CRUD execute、各 cue store、提示词、admin
- Go：一期 **不强制**拆 batch；二期分 create/update/delete API
- Hub：类型/查史播报页演进为 OP/分层飞轮整理；缺口仍 TIME（及可选 QTY）
- 存量短关键词飞轮需迁移或清空，避免与「整段」策略冲突
