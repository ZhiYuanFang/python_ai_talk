## 1. 相对配方与物化

- [x] 1.1 定义相对配方 schema（kind / points.day|period|hour|minute / duration_minutes）与校验
- [x] 1.2 实现 `materialize(formula, now_shanghai) → (start_unix, end_unix)`；失败当 miss

## 2. 飞轮与 resolve

- [x] 2.1 新增 `time_cue_store`（`feeding_time_cues`，整段 document，仅合法配方可写）
- [x] 2.2 `dim_resolve.resolve_time`：规则 → 飞轮物化 → LLM → 配方回写；接 rule_gap
- [x] 2.3 `segment_multidim` TIME 段改接 `resolve_time`；`read` 跳过

## 3. TIME LLM 契约

- [x] 3.1 改 `SEGMENT_TIME_LLM_PROMPT`：主出相对配方（可附带当次 unix）
- [x] 3.2 改 `llm_resolve_time`：校验配方；仅 unix 可当次用、不写飞轮

## 4. Admin

- [x] 4.1 `/v1/admin/time-cache` list/bulk/delete；bulk 拒绝无配方/仅 unix 条目
- [x] 4.2（可选）种子常见相对口语整句

## 5. 验收

- [ ] 5.1 手工：昨晚八点喂了 → 冷路径写配方（非 Unix 主载荷）
- [ ] 5.2 手工：次日同句 → 飞轮物化、无 TIME LLM
- [ ] 5.3 手工：模型仅 unix → 当次可落库、库中无该 document
- [ ] 5.4（可选兄弟仓）Hub 时间飞轮页
