## Context

pending 澄清（`parent_disambiguation` / `leaf_confirm`）在同一 `/intent` + `conversation_id` 下用 `resolve_free_text` 分层解析。当前顺序为：子名 → 序号 → 拒绝词 →（仅 leaf_confirm）肯定词 → 其余 `OFF_TOPIC` 清 pending 当新意图。肯定/拒绝为精确集合匹配，不做句末标点剥离；复合句无法表达「确认并带数量」「否定并改选」。

原 `parent-event-disambiguation` design 否决「每轮 LLM」以控成本。本变更采用 **硬匹配优先、miss 后 LLM 兜底**，且 LLM 为窄澄清解析器（非整图意图分类）。

## Goals / Non-Goals

**Goals:**

- 硬匹配归一化后仍 miss 时，用带 pending 语境的 LLM 解析复合回复
- 支持 `confirm` / `select` / `correct` / `reject` / `new_intent` / `ask_again`
- `confirm` 带 quantity 时覆盖 `pending.quantity`
- `correct`：点名叶子直接落库；点名父则进入父消歧；飞轮最终叶子落地时写消歧前原话
- LLM 基础设施失败 → `ask_again`，保留逃逸口（LLM 显式 `new_intent`）

**Non-Goals:**

- 不改 `/intent` 请求/响应主契约
- 不恢复 `confirm|reject` 枚举按钮主路径
- 不做向量显式 decrement API（否定靠不对旧 `matched_vector_id` 做 `success_count++`）
- 不做同音/繁简/语气助词白名单扩展（交给 LLM）
- 不把澄清解析并入完整 `classify_intent` 大 prompt

## Decisions

### 1. 分层：归一化硬匹配 → LLM 澄清 → 动作落地

- **选择**：`normalize` → 现有硬匹配 → miss 则 `llm_resolve_pending_reply` → 映射到扩展 `ResolveResult`
- **理由**：短回复零成本；复合句需要语境；与「非默认每轮 LLM」一致
- **替代**：一律当新意图 —— 否决（丢掉 pending 事件）；每轮都 LLM —— 否决（成本）

### 2. LLM 输出动作枚举

```
confirm     确认当前 leaf_confirm 候选（可带 quantity）
select      选中 pending.options 内某一项（可带 quantity / event_id）
correct     否定当前猜想，改到某事件（可在 options 外）
reject      纯取消
new_intent  离题，清 pending 冷启动
ask_again   不确定，保持 pending 再问
```

- **父消歧下裸肯定**（如「是的」且无选中项）：LLM SHOULD 输出 `ask_again`，不得臆造 `confirm`
- **替代**：只返回 yes/no —— 否决（无法覆盖复合句）

### 3. correct 落地规则

- **选择**：
  - 目标为**叶子**：清旧 pending，**直接**作为喂养结果落地（可带 quantity）
  - 目标为**父**：清旧 pending，创建新的 `parent_disambiguation` pending
  - 无法解析到事件字典内事件：`ask_again` 或 `new_intent`（由 LLM；实现侧对非法 id 回退 `ask_again`）
- **理由**：用户已点名叶子，再确认一轮体验差；父仍不可落库
- **替代**：叶子也强制 need_confirm —— 否决（用户已明确）

### 4. quantity 覆盖

- **选择**：`confirm` / `select` / `correct` 若解析出 quantity，**覆盖** pending 原 quantity（含原为 null）
- **理由**：产品示例「是的，喂了30毫升」以本句数量为准

### 5. 飞轮

- **选择**：仅最终唯一叶子落地时，`add_user_expression(消歧前原话 → 最终叶子)`；不对旧错误 `matched_vector_id` 调用 `increment_success_count`；短回复/复合回句本身不入库
- **理由**：纠正后教会「原话应对应正确叶子」；旧向量 match 已计、success 不计即负向
- **替代**：飞轮写复合回句 —— 否决；显式 decrement —— 首版不做

### 6. LLM 失败策略

- **选择**：超时 / 非 JSON / 缺字段 → `ask_again`（保持 pending，返回原澄清问句）
- **理由**：避免误清会话；逃逸仍靠 LLM 成功返回 `new_intent`，或用户改口说序号/名称硬匹配
- **替代**：失败当 `new_intent` —— 否决（易误清）

### 7. 硬匹配归一化

- **选择**：`strip`；去掉句末 `[。．.!！?？]+`；英文 `casefold`；再查 YES/REJECT/序号/名称
- **理由**：修复「是的。」；与序号已有剥标点对齐
- **不做**：中间逗号句（「是的，喂了30毫升」）仍走 LLM

### 8. 调用与异步

- **选择**：澄清 LLM 走现有 `llm_client` + 请求携带的 `model_config`；`resolve` / `try_handle_pending` 需变为 async（或 pipeline 层 async 包装调用）
- **理由**：与意图分类一致；路由已是 async

## Risks / Trade-offs

- [LLM 误判 confirm/select] → prompt 强约束 options；父消歧禁止裸 confirm；非法 event_id 回退 ask_again
- [LLM 连续失败卡住] → 首版可接受；后续可加「连续 N 次 ask_again → 提示改用序号」
- [correct 直落叶子误选] → 依赖 LLM + 事件名字典校验；错了用户可用新意图纠正
- [多一次延迟与费用] → 仅硬匹配 miss 才调用
- [async 改造波及面] → 集中在 clarification + intent_pipeline + 路由调用点

## Migration Plan

1. 落地归一化与扩展 ResolveResult / 动作处理
2. 接入澄清 prompt + LLM 调用与失败回退
3. correct 叶子直落 / 父消歧 + 飞轮约定
4. 回归：是的。；是的，喂了30毫升；不是的，是xxx；父消歧裸是的；LLM 失败再问；离题 new_intent

## Open Questions

- 无（「点名叶子则直接落」已确认）
