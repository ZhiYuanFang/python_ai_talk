## 1. 提示词与字典匹配

- [x] 1.1 更新 `intent_classification.py`：删除 `remark_probe_hint` 注入；保留进行中摘要；增加「简称/进行态对表内真名」与「专名不得常识升格」两条原则；去掉依赖备注探针的字段旁白
- [x] 1.2 加强 `_match_feeding_event`（或抽出共享函数）：精确 → 包含 → 剥「正在」「在」等前缀后再包含；`classify_intent` 与多事件子项共用

## 2. 收窄分类前探针

- [x] 2.1 将 `remark_probe` 收窄为仅进行中摘要（可改名）；删除 `extract_oov_token` 门控的备注 filter、`remark_probe_hint` 写入
- [x] 2.2 更新 `IntentState`、思考/流式文案：去掉备注探针摘要相关状态与「正在按备注查找」类分类前文案（反查步骤可另配思考语）

## 3. 分类后备注反查

- [x] 3.1 实现备注反查：对顶层与 `events[]` 中字典未命中的名称，调 `get_filtered_history_events(remark=名称, 空 eventIds, 近窗, 小 limit)`，按 `event_id` 聚合
- [x] 3.2 唯一命中：写入字典 `event_id`/`event_name`、`remark_keyword`；多命中：消歧 pending（选项为命中叶子）；零命中：无法识别文案，禁止 `is_new_event`，不猜常识事件
- [x] 3.3 接入 `intent_graph`：缓存 miss → 进行中 → classify → 备注反查 → 既有确认/执行/查记录路由；中文注释说明业务场景

## 4. 确认与管线对齐

- [x] 4.1 反查消歧与既有 `clarification` / `intent_pipeline` 续聊打通（选叶子后带上 `remark_keyword`）
- [x] 4.2 查记录确认话术在带备注时点出字典事件名与备注专名；零命中不进入可落库确认

## 5. 手工验收

- [x] 5.1 对照规格：上一次 AD（唯一营养品）、AD 多叶子消歧、首次记 AD 无法识别、正在爬→爬练习且不反查、分类提示无备注摘要且有进行中、删除上一次坐练习仍为 delete
