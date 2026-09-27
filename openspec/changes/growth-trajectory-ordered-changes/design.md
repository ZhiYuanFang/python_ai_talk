## Context

现网：`GROWTH_TRAJECTORY_SYSTEM_PROMPT` 约 200 字；`generate` 建议结构以「注意事项」为主体，并禁止按日分节；`plan` 判 `enough` 可直达 `generate`，仅满 6 轮才强制 `final_free_text`。

目标：7 日内**明确、有序**的可能变化（如：已会站 → 缠人要站 → 扶物站 → 尝试迈步），提问尽量摸清细节，生成前必有家长自述兜底。

## Goals / Non-Goals

**Goals:**

- 产出主段 = 编号阶梯式可能变化；禁日历日；字数约 400～600。
- plan 挖能力边界；choice=2；细挖 free_text。
- 任意路径进 generate 前必经一次 final free_text。

**Non-Goals:**

- 不改 max_structured_rounds=6 的数值（除非实现需要微调文案）。
- 不改为日历日程（第 1 天…）。
- 不扩展 choice 为多于 2 选项。
- 不改喂养史聚合与画像拉取。

## Decisions

### D1: 生成结构

```
## 🌟 未来N天可能发生的变化（主）
1. …
2. …
3. …
## ⚠️ 需要注意什么（辅）
## 🍼 结合近期喂养（弱史可弱化）
## 💛 小结
```

- 阶梯：发展先后或「更可能先出现」顺序；每条可观察行为。
- 禁止「第1天」「第2天」等主要分节。
- system/user 共同约束约 400～600 字（以中文篇幅为导向，非字节精确计数）。

### D2: plan 提问策略

- 未摸清「当前会什么 / 扶站稳否 / 有无迈步意图」等边界时倾向 `ask`，且优先 `free_text` 细挖。
- 二元确认仍可用 `choice`（恰好 2 选项）。
- `enough` 仅表示结构化问答可结束，**不**等于可跳过末问。

### D3: enough → final_ask → generate

```
plan enough + !final_ask_done  → final_ask（强制 pending free_text）
plan enough + final_ask_done   → generate（理论上不应再发生）
满轮 !final_ask_done           → final_ask（保持）
final_free_text                → generate
```

- `route_after_plan`：`enough`/`generate`/`done` 在未 `final_ask_done` 时路由到 `final_free_text`，而非 `generate`。
- 或在 `plan_next` 将 enough 改写为 `final_ask` 并写入兜底题——二选一，推荐 **plan_next 内改写**，路由表更简单。

### D4: 末问文案

- 保持「这是最后一次提问」硬约束；引导补充能力/兴趣/环境等与 7 日阶梯相关的自述。

## Risks / Trade-offs

- [多一轮交互] → 产品接受；换更准阶梯。
- [字数放宽 token] → 可接受；主段优先时可截断辅段。
- [模型仍写日历日] → 提示词强约束 + 验收关注。

## Migration Plan

1. 改 system / generate / plan 提示词。
2. 改 plan_next：enough 且未 final → final_ask。
3. 手工：早停 enough 仍出现末问；生成主段为编号阶梯。

## Open Questions

- 无。
