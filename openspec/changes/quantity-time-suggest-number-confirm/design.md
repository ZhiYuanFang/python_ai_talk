## Context

分类提示已向 LLM 注入叶子 `type=time|number|one` 与 `quantity` 字段，但未约束「有毫升却选计时叶」。`match_feeding_event` 对「母乳」精确命中计时叶后不再考虑「瓶喂母乳」。叶子确认走 `leaf_confirm`；`create_leaf_confirm_pending` 已支持 `confirm_message or build_leaf_confirm_message(...)`，但须保证冲突改选时分类产出的非空问句一路传到 pending，不被后续逻辑清空。

产品定调：近义由 LLM 判断；不问二选一列表，而是改选计量叶后用简洁单句确认（「您是要记录瓶喂母乳x毫升嘛？」）；缓存命中不管。

## Goals / Non-Goals

**Goals:**

- Classify system 提示增加通用冲突规则：quantity +（本会落到）time → 找近义 number → 填计量叶 + 简洁 `confirm_message`。
- 冲突改选场景保留/优先 LLM `confirm_message`；提示要求问句力求简洁。
- 内部 reasoning 须中文，并体现对 `type` 与近义计量叶的核对。

**Non-Goals:**

- 不改缓存命中 / overlay / 落库前规则改叶。
- 不做代码侧近义扫描（包含名、同父等）强制改写。
- 不新建 parent_disambiguation 式多选项 UX。
- 不写测试文件。

## Decisions

### D1: 提示驱动改选 + leaf_confirm，非多选消歧

- **选择**：LLM 将 `events[]` 目标改为近义 `number` 叶，`need_confirm` 仍走现有 leaf_confirm；问句由 `confirm_message` 表达建议计量记录。
- **备选**：options 二选一 → 用户明确不要；代码静默改瓶喂 → 与「询问」不符。
- **理由**：复用现有确认/correct 路径；否定可用 correct 改回计时叶。

### D2: 近义仅 LLM

- **选择**：不在 Python 用名称包含/同父找 number 叶。
- **备选**：规则兜底 → 更稳但本 change 明确排除。
- **理由**：产品要求思考在模型侧；字典命名多样时规则易误伤。

### D3: confirm_message 优先且简洁

- **选择**：提示要求冲突改选时输出简短确认句（可给一句示例模板）；pipeline/`create_leaf_confirm_pending` 在 `confirm_message` 非空时 MUST 用之，不得被 `build_leaf_confirm_message` 无条件覆盖。
- **现状**：clarification 已是 `confirm_message or build_...`；实现阶段核对 classify → postprocess → pending 全链路未丢字段。
- **空问句**：仍回退模板（「您是要{slot}吗？」），保证有确认话术。

### D4: 无近义 number 时

- **选择**：找不到近义计量叶则保持原 time 叶确认路径（不编造表外事件）。
- **理由**：与「禁止编造 id」一致。

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 模型仍填计时母乳 | 提示强调禁止将 quantity 记到 time；示例「60毫升母乳」；抽检 |
| 问句过长/啰嗦 | 提示明确「confirm_message 力求简洁」 |
| LLM 问句与落库叶不一致 | 条文要求 event 填 number 叶且问句点名同一叶名 |
| 仅提示无代码兜底偶发失败 | 接受；后续若不够再加规则 change |

## Migration Plan

1. 部署提示与确认传递修复（若有）即可，无数据迁移。
2. 回滚：还原 system 模板与相关传递逻辑。

## Open Questions

- （已决）近义 LLM；询问单句建议计量叶；缓存不管；confirm_message 优先且简洁。
- 无近义时保持 time 确认（见 D4）。
