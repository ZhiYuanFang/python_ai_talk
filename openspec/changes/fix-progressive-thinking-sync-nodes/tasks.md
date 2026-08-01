## 1. 兼容 sync/async 节点调用

- [x] 1.1 在 `progressive_thinking.py` 增加统一 `_invoke_node`：调用后 `inspect.isawaitable` 再 await，否则直接当 patch
- [x] 1.2 `run_one_step_with_thinking` 与 `run_linear_steps_with_thinking` 改用该辅助；更新类型注解允许 sync Callable

## 2. 校验

- [x] 2.1 确认 intent stream 对 `match_event_by_vector` 不再 TypeError；async 节点路径仍可 await
