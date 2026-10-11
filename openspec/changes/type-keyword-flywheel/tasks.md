## 1. 类型关键字库与 Admin

- [x] 1.1 新增类型集合 store（如 `feeding_type_cues`）：search/add/list/bulk 跳过/dedupe/delete；payload=`target_type`/`op`/`history_mode`
- [x] 1.2 新增 `/v1/admin/type-cache`（list/bulk/dedupe/delete），镜像 intent-cache 约定；注册路由
- [ ] 1.3（兄弟仓）Go Hub：类型向量整理页 + 反代 type-cache API

## 2. TYPE 路径改造

- [x] 2.1 扩展 `SEGMENT_TYPE_LLM_PROMPT`：`need_confirm` + `keywords[]`；查史/结束/记录示例；弱喂养词不得默认 create
- [x] 2.2 `resolve_type`：类型飞轮优先 → TYPE LLM；删除「睡/吃」弱线索 create 短路；SHAPE 主路径并入 TYPE
- [x] 2.3 高置信：采用结果并按 keywords 写类型库；`need_confirm=true`：确认后再写
- [x] 2.4 停用独立 SHAPE 小 LLM 主路径调用与 shape 缺口写入

## 3. 缺口箱收窄

- [x] 3.1 停止 `rule_gap` 写入 type / shape / event；缺量追问不写（或 Hub 不可见）
- [x] 3.2 TIME/QTY 仅在规则 miss 且调用 LLM 时写缺口（`llm_used=true`）
- [x] 3.3 `rule_gaps` admin 默认列表仅 time|quantity
- [ ] 3.4（兄弟仓）Hub 规则缺口页默认只展示 TIME/QTY；可选清理存量 JSONL

## 4. 验收

- [ ] 4.1 手工：「睡了多久了」→ history 查史（非记睡眠）；再次同说法可飞轮加速
- [ ] 4.2 手工：「睡着了」create 开表；「睡醒了」end
- [ ] 4.3 手工：Hub 类型向量可 list/bulk/删；缺口列表无 type/event/shape 噪音
