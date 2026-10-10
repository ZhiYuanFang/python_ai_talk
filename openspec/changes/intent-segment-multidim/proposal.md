## Why

整句向量命中后整包回放 `events[]` 并免确认，会把「换尿布，发现拉臭臭了」串到复合句「换尿布了，洗澡了，吃了120奶，睡觉了」，漏记其它事件且跳过尿尿/拉屎消歧。LLM 一次吐满血多 `events` 提示重、易幻觉、偏慢。需要改成「单事件本地多维 / 复合句仅分句再段级拼装」，并删除一次结构化旧路径；非事件维不自动飞轮，规则缺口落库供 Hub 人工扩规则。

## What Changes

- **BREAKING**：删除「整句 → 整包意图」缓存命中免确认路径，以及 `classify_intent` **一次结构化多 events** 的主路径与对应提示契约。
- **BREAKING**：`feeding_intents` 语义改为 **短说法 → 事件**（`event_id` / kind）；发版清空重建，**不**迁移旧整包 payload；阈值仍 **0.72**。
- 管道：像单事件 → **零 LLM** 段级多维；复合 → **LLM 仅分句**（可带句级 `target_type`）→ 循环 TYPE→EVENT→SHAPE→QTY→TIME → 拼装。覆盖 create / read / update / delete / end。
- 分句失败或任一段定不出类型/事件 → **引导重说**，禁止回退一次结构化。
- 确认策略 **C**：阻塞项（number 缺量追问、create 父消歧）优先；短同质多段一次拼问；长或混 op 逐段确认。
- 飞轮边界：仅 **事件维** 越用越快；TYPE/TIME/QTY 等规则 miss（及 LLM 兜底）写入 **规则缺口收件箱**，供人工改代码规则。
- 交付顺序：**先改 Python**（管道、事件库、缺口 API）；**再改 Go Hub**（缺口列表页代理与 UI）。

## Capabilities

### New Capabilities

- `intent-segment-multidim`：分句判定、段级多维拼装、失败重说、确认形态 C、删除一次结构化主路径
- `intent-event-phrase-flywheel`：短说法事件向量库（替代整包意图缓存语义）；清空重建与种子约定
- `intent-rule-gap-inbox`：非事件维规则缺口落库与 Python admin API；Go Hub 页后续接入

### Modified Capabilities

- `langgraph-intent-graph`：入口改为单事件多维 / 复合分句多维，移除整包 cache→overlay→免确认执行与满血 classify 主链
- `feeding-intent-user-confirmation`：多段确认改为 C（短拼问 / 长混装逐段）；number 缺量须追问
- `parent-event-disambiguation`：挂到段级结果——create 父消歧、read 父展开（行为对齐既有，入口改段流水线）
- `feeding-intent-vector-matching` / `feeding-intent-data-flywheel`：不得再以整句整包意图回放作为飞轮单位；事件匹配改为短说法库

## Impact

- **Python**：`intent_graph`、`classify_intent`、`match_intent_cache`、`overlay_slots`、`intent_cache_store`、`intent_pipeline` / `clarification`、新分句与多维服务、规则缺口存储与 `/v1/admin/rule-gaps`、启动 `CLEAR_FEEDING_INTENTS_ON_STARTUP` 发版剧本、字典短说法种子。
- **Go（二期）**：Hub 代理 rule-gaps API 与管理页；本仓 tasks 分阶段，Go 实现可在兄弟仓跟进。
- **对外**：`/v1/analyze/intent` 响应壳尽量兼容；行为上复合句/缓存命中路径 **破坏性** 变化。
- **运维**：清库后需灌事件短说法种子；缺口箱默认 Python volume，不写 MySQL。
