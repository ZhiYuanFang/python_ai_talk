## 1. llm_client 去掉换模

- [x] 1.1 `invoke` 改为仅对传入唯一 model 调用一次；缺 model 立即抛错；删除保底候选循环
- [x] 1.2 删除或停用 `parse_llm_fallback_models`、`_build_candidate_configs` 保底段、`is_recoverable_llm_error`（若仅服务换模）；更新模块中文注释（保留闸门，不新增同模 LLM N 次重试）
- [x] 1.3 从 `settings` / `.env.example` / env 模板移除 `LLM_FALLBACK_MODELS`（或明确废弃注释）；保留各 provider key 供 Go 选型

## 2. HTTP 契约与口径

- [x] 2.1 intent / care_alert：`model` 改为必填或省略即明确失败；去掉「缺省走保底序」注释与路由空 dict 保底语义
- [x] 2.2 clinic/tip 与其它调用点注释对齐：Python 不参与 VIP、不换模

## 3. 失败文案

- [x] 3.1 抽出共享文案常量「脑电波过载，请稍后重试」
- [x] 3.2 `classify_intent` 失败软回执改用该文案；流式上下文可 `emit_thinking` 同句
- [x] 3.3 扫其它 `llm_client.invoke` 软失败/用户可见路径，能对齐的统一同句

## 4. 验收

- [x] 4.1 手工：有 model 成功路径不变；人为上游失败不再串行换模且尽快返回脑电波文案；无 model 立即失败
- [x] 4.2 `openspec validate remove-llm-fallback-fail-fast --strict` 通过
