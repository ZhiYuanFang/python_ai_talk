## Context

Clinic 主路径已统一为 LangGraph（含隐式飞轮入口与 progressive thinking）。隐式采纳会更新通识知识块的 `quality_score`，但 `vector_store` 检索仍主要按相似度排序，优质内容无法优先/硬过滤。产品已去掉 👍/👎，显式 `/v1/clinic/feedback`、`/v1/tip/feedback` 成为死路径且 `answer_id` 常无法对应 chunk id。

目标：在被采纳的高质量问答上建立**全局 Q&A 捷径**；下次相似问句在月龄带与质量达标时直接回答；通识检索加质量硬过滤；下线显式 feedback。

## Goals / Non-Goals

**Goals:**

- 多轮问句经 LLM 改写为独立问句后检索全局 Q&A；命中则跳过 clinic 完整 prepare。
- 仅隐式 `accepted` + 本轮改写成功时写入 Q&A。
- 生日→月龄共享逻辑；clinic 提示词用月龄；月龄带规则统一。
- 通识检索 `quality_score` 硬过滤。
- 删除 Python clinic/tip 显式 feedback 接口与文档兼容描述。

**Non-Goals:**

- 本仓不强制改 Go/Flutter（仅标注协调点；Python 删除后对端 404）。
- Tip 图不做 Q&A 捷径（仅共享月龄推导与通识硬过滤若 tip 走同一 store）。
- 不做跨设备个性化 Q&A（全局库 + 月龄带即可）。
- 不改变 needs-history / force_needs_history 的语义，仅规定此类请求不走捷径。

## Decisions

### 1. Query key = LLM 改写独立问句

- **选择**：检索与入库都用「多轮 → 独立问句」改写结果；改写失败/超时 → **miss**，不以原文 query 回退检索 Q&A。
- **理由**：指代消解后相似度才稳定；原文回退易误命中历史轮次噪声。
- **备选**：原文+历史拼接 embedding — 拒绝，噪声大且难与入库 key 对齐。

### 2. 全局 Q&A store + age_band

- **选择**：独立 Chroma collection（或等价命名空间）`qa_fast_path`（名称实现时可常量）；metadata 至少含 `age_band`、`quality_score`、`standalone_question`、答案正文/引用字段；**全局**共享，不按 `device_no` 隔离。
- **理由**：同类月龄问题可跨设备复用；与通识知识库分离，避免捷径答案污染通识检索。
- **备选**：按设备隔离 — 拒绝，冷启动慢。

### 3. 月龄带规则

- `months < 36` → `m{N}`（N = 整月，与 tip `derive_baby_age` 一致）。
- `months >= 36` → `y{Y}`（Y = floor(months/12)）。
- 未知月龄（无生日/解析失败）→ **不命中**捷径，也不写入依赖 age_band 的条目（或写入时跳过）。
- 将 tip 的生日解析/月龄计算抽到 `app/shared/`（或共享模块），tip 节点变薄包装；clinic 飞轮后与提示词共用。

### 4. 命中条件（默认阈值）

同时满足才 hit：

| 条件 | 默认 |
|------|------|
| 向量相似度 | `> 0.8` |
| Q&A `quality_score` | `>= 0.7` |
| `age_band` | 与当前宝宝一致 |

命中后：用库中答案作为 clinic 回复（可轻量包装人格语气，但**不**再跑 judge_data / fetch_history / 通识检索 / 完整 answer 生成）；thinking 可发一句「命中历史优质问答」类短讯。

未命中：现有 prepare 链路不变。

### 5. Clinic 图形状

```
implicit_feedback → fetch_baby_profile → derive_baby_age
  → rewrite_standalone_question → search_qa_fast_path
  → (hit) → format_qa_answer → END
  → (miss) → judge_needs_history / 现有 prepare …
```

- 写入 Q&A：在隐式采纳成功分支内（或飞轮节点尾部），仅当 `accepted` 且本轮已有成功的 `standalone_question`；答案取本轮最终 clinic 回答。
- Intent 嵌套 clinic：同一图，捷径同样生效；`force_needs_history` / 历史点查意图 → 跳过 search 或强制 miss。

### 6. 捷径拦截

以下强制 miss（不查或查了不算 hit）：

- `force_needs_history == true` 或判定为历史点查类意图。
- 敏感医疗（复用现有敏感/拒答策略若有；否则在 rewrite/search 旁加轻量规则或 prompt 标记 `block_fast_path`）。
- 改写失败、超时（默认 **2s**）、未知月龄。

### 7. 通识知识硬过滤

- 在现有 knowledge `query` 路径：召回后（或 where 过滤）丢弃 `quality_score < 0.7`（可配置常量）。
- 与捷径库阈值可同可分；默认同为 0.7。
- 隐式反馈继续更新通识 chunk 分数；不再依赖显式 feedback。

### 8. 下线显式 feedback（BREAKING）

- 删除 `clinic.py` / `tip.py` 的 `/feedback` 路由实现与模块注释中的兼容说明。
- 评估删除或收缩 `FeedbackRequest`（若无其它引用则删）。
- 更新 `docs/deploy-guide.md` 等：去掉显式反馈兼容描述。
- **跨仓**：Go 客户端/controller、Flutter 按钮调用需另行移除；本 change 部署后 Python 返回 404。

### 9. 配置与可观测

- 常量/环境变量：`QA_SIM_THRESHOLD=0.8`、`QA_QUALITY_MIN=0.7`、`KNOWLEDGE_QUALITY_MIN=0.7`、`REWRITE_TIMEOUT_S=2`。
- 日志：rewrite miss 原因、hit/miss、写入跳过原因（无改写/无月龄）。

## Risks / Trade-offs

- [错误捷径答案传播] → 质量硬阈值 + 仅 accepted 入库；后续可对 Q&A 条目也做质量衰减（本期可选：入库初始分 0.8，被再次采纳再加分）。
- [改写延迟拖慢 TTFT] → 2s 超时即 miss；thinking 流可先发「整理问题…」。
- [全局库隐私] → 只存去标识后的独立问句与通用育儿答，不入设备号；敏感类拦截。
- [Go/Flutter 仍调 feedback] → 部署协调；短期 404 可接受。
- [月龄边界误匹配] → 带边界（如 35↔36）可能漏命中，宁可 miss 也不跨带。

## Migration Plan

1. 部署带新 collection 与硬过滤的代码；旧知识无 `quality_score` 的按现有默认 0.8 处理。
2. 同版本删除 feedback 路由；通知 Go/Flutter 停调。
3. 回滚：恢复旧路由与关闭捷径边（feature flag 可选：`QA_FAST_PATH_ENABLED`，默认开）。

## Open Questions

- Q&A 命中后是否完全跳过人格/语气二次生成，还是只跳过检索与数据准备？（默认：轻量 format 节点套闺蜜语气，不重跑完整 clinic_answer 长链。）
- 敏感医疗拦截是否已有可复用节点？实现时优先复用，否则最小规则集。
