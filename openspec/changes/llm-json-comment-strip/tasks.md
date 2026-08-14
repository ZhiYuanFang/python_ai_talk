## 1. 共享工具

- [x] 1.1 新增 `app/shared/llm_json.py`：引号安全去注释（`//`、`/* */`，可选字符串外 `#` 行）；中文注释说明业务与陷阱
- [x] 1.2 实现 `loads_llm_json`：去围栏 → 去注释 → loads（可含抠 `{...}`）；失败抛出或返回明确错误供调用方处理

## 2. 解析点接入

- [x] 2.1 `classify_intent._parse_intent_result` 改用共享加载
- [x] 2.2 `clarification._parse_llm_clarify_json` 改用共享加载
- [x] 2.3 care_alert `_extract_json_object` 改用共享加载（或内部调用同一去注释）
- [x] 2.4 `judge_data_requirement` / `judge_needs_history`（及 grep 扫到的其它 LLM `json.loads`）接入共享工具

## 3. 验收

- [x] 3.1 手工：带 `//` 注释与含 `http://` 字段的样例可解析；去注释后仍非法则走原降级
- [x] 3.2 `openspec validate llm-json-comment-strip --strict` 通过
