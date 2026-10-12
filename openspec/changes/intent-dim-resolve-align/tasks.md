## 1. 维判定统一骨架

- [x] 1.1 文档化并落地各维 `resolve_*` 调用形状（规则→整段飞轮→LLM→回写/gap）；中文注释
- [x] 1.2 拆出 `resolve_read_source` / 保持 TIME 无飞轮特例与现有 rule_gap 行为

## 2. history_speak 硬切整段

- [x] 2.1 `history_speak_cue_store`：命中/写入仅整段；停用 `add_keywords` 主策略；阈值对齐 OP
- [x] 2.2 `resolve_history_speak_policy`：LLM 成功只回写整段原文；拒绝短词热路径
- [x] 2.3 清空或失效旧短词条目；种子改为整句（睡了多久了等）；更新/替换 `seed_history_speak_cues.py`

## 3. R·predict 与 U/D 定位补齐

- [x] 3.1 新增 `feeding_predict_cues` store + admin；`resolve_predict_dims` 接线 speak_predict / read+predict
- [x] 3.2 新增 `feeding_locate_cues` store + admin；`resolve_locate` 接线 U/D；payload 不含 historyId
- [x] 3.3 OP LLM 成功后拆写 OP / source / predict 各层（避免只写一层）

## 4. 事件回写与种子

- [x] 4.1 事件冷路径（LLM 定叶）成功后以段整句回写事件飞轮
- [x] 4.2 整句种子脚本覆盖 OP/source/speak/predict 金线话术
- [ ] 4.3（兄弟仓）Hub 页对齐整段播报 / predict / locate admin

## 5. 验收

- [ ] 5.1 手工：睡了多久了 → 整段 speak 飞轮可跳过播报 LLM（二次）
- [ ] 5.2 手工：还有多久醒来 → predict 飞轮二次可跳过预测维 LLM；禁止上一次用时
- [ ] 5.3 手工：短词「多久了」单独不再误命中复合句播报策略
- [ ] 5.4 手工：时间 miss 仍 rule_gap；口语量二次仍走 qty 飞轮
