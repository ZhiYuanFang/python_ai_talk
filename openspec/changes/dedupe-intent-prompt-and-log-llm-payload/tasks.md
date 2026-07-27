## 1. 意图分类 user 去重

- [x] 1.1 修改 `build_intent_classification_user_message`：去掉 `event_dictionary` 参数与「可用事件类型」列表，仅保留用户输入与分析指令
- [x] 1.2 修改 `classify_intent.py`：调用改为 `build_intent_classification_user_message(text)`
- [x] 1.3 确认 `build_intent_classification_system_prompt` 仍注入事件 id+name 目录

## 2. LLM 请求 INFO 全量日志

- [x] 2.1 在 `llm_client.invoke` 中于模型调用前 INFO 打印 provider、model、完整 system_prompt、完整 messages
- [x] 2.2 在 `llm_client.stream` 中于流式调用前做同等 INFO 打印
- [x] 2.3 日志格式便于检索（如统一前缀/分隔标记）

## 3. 非回归核对

- [x] 3.1 确认未改动其它 prompts（data_requirement / clinic / tip / history / suggest）
- [x] 3.2 确认未改动 `event_cache` TTL 与飞轮相关代码
- [x] 3.3 冒烟：意图 LLM 降级路径仍可分类；日志中可见完整发送载荷且 user 侧无事件名列表
