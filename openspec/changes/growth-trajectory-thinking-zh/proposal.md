## Why

成长轨迹在启用原生 thinking 时，会把提供商 `reasoning_content` 原样透出到 SSE；当前 system 提示只约束最终 JSON/Markdown，**不约束内部思考语言**，导致家长侧看到英文思考过程，与产品中文体验不一致。

## What Changes

- 在成长轨迹共用 system 提示（`GROWTH_TRAJECTORY_SYSTEM_PROMPT`）中增加约束：**内部思考 / reasoning 须使用中文**。
- 同步更新该文件业务说明：由「不指导思考写法」改为明确约束思考语言。
- 不改变 SSE 事件类型、编排字幕逻辑、LLM 透传链路；不强制翻译已生成的英文增量。

## Capabilities

### New Capabilities

- `growth-trajectory-prompts`: 成长轨迹 LLM 提示词约定（含内部思考语言为中文）

### Modified Capabilities

- （无）基线尚无成长轨迹提示词能力；本变更以新建 capability 落行为要求。

## Impact

- 代码：`app/growth_trajectory/graphs/nodes/prompts/system.py`
- 行为：`confirm_prior` / `plan_next` / `generate` 等经该 system 的流式调用，模型侧 reasoning 语言期望为中文（仍依赖模型遵从；非硬保证）
- API / 编排图拓扑 / `llm_client`：无变更
