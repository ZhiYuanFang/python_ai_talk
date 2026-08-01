## 1. 删除死代码

- [x] 1.1 从 `generate_response.py` 移除 suggest 分支与 `suggest_answer` import；仅保留 history_answer；更新模块说明
- [x] 1.2 删除 `app/clinic/graphs/nodes/prompts/suggest_answer.py`
- [x] 1.3 grep 确认无残留引用；确认 intent history 边仍指向 `generate_response`
