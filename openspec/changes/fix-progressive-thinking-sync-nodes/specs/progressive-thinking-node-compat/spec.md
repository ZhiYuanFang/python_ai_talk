## ADDED Requirements

### Requirement: Progressive thinking invokes sync and async nodes safely

`run_one_step_with_thinking` 与 `run_linear_steps_with_thinking` 在 yield thinking 之后执行节点时，SHALL 支持同步节点（直接返回 patch dict）与异步节点（返回 awaitable，再解析为 patch）。SHALL NOT 对同步返回的 dict 使用无效的 `await` 导致 TypeError。

#### Scenario: Sync match node on intent stream

- **WHEN** intent 流式步进调用同步的 `match_event_by_vector`
- **THEN** 步进助手 SHALL 成功取得 patch 并合并进 state，且不抛出 `TypeError: object dict can't be used in 'await' expression`

#### Scenario: Async node still awaited

- **WHEN** 步进助手调用 async 节点（如 `classify_intent`）
- **THEN** 系统 SHALL await 该协程并将返回的 dict 合并进 state

### Requirement: Thinking-before-execute order unchanged

兼容 sync/async 后，系统 SHALL 仍先向调用方 yield thinking 文案，再执行节点函数。

#### Scenario: Thinking precedes sync node work

- **WHEN** 对同步节点执行一步步进
- **THEN** 消费者先收到 `(node_name, thinking_text)`，之后节点才运行并更新 state
