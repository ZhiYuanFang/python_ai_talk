## 1. Companion session store

- [x] 1.1 在 `app/shared` 新增陪伴会话数据模型（turn：user/assistant；last_suggestion：answer_id、knowledge_ids、text、feedback_applied 等）
- [x] 1.2 实现 Redis 会话存储（key=`companion:session:{device_no}`，读写、追加轮次、截断为最近 5 轮、TTL 7 天滑动续期），复用现有 Redis 连接方式并加中文业务注释
- [x] 1.3 在配置中增加会话 TTL / 最大轮次数常量（默认 7 天、5 轮），避免魔法数散落

## 2. Tip / clinic 会话接线

- [x] 2.1 tip 流式成功后：合成 user（刚记录了「event_name」）+ assistant=tip 全文写入会话，记录 last_suggestion（含本轮 knowledge_ids）
- [x] 2.2 clinic 流式成功后：追加 user=question + assistant=回答，更新 last_suggestion 与 knowledge_ids
- [x] 2.3 tip / clinic 生成前读取会话近 5 轮，注入提示上下文（与喂养 history_events 分离）
- [x] 2.4 确保 tip 检索结果中的真实 doc_id 能传到会话层（必要时在图 state / 路由累积字段中透传）

## 3. 隐式建议采纳与飞轮

- [x] 3.1 在 `app/shared` 实现三态判定（accepted/rejected/unclear）：输入为本轮用户话 + 上一条建议文本，输出结构化三态；异常时失败可重试
- [x] 3.2 clinic 生成回答前：若 last_suggestion 且未 feedback_applied，执行判定；accepted/rejected 且 knowledge_ids 非空则调用 `vector_store.update_quality_score`；三态成功后均标记 feedback_applied
- [x] 3.3 tip 开场写入后 last_suggestion.feedback_applied=false，保证首次 clinic 续聊可判定 tip
- [x] 3.4 保留现有 `/v1/clinic/feedback` 与 `/v1/tip/feedback` 接口不删除

## 4. 闺蜜人格提示词

- [x] 4.1 改写 `clinic_answer` 系统/用户提示：懂娃闺蜜、对家长口语、知识当背景、安全边界闺蜜口吻
- [x] 4.2 改写 `tip_answer`：口语短陪伴；去掉强制「## 当下总结 / ## 下一步注意事项」结构
- [x] 4.3 改写 `suggest_answer`（及若共用的 conversation 生成路径）与 clinic/tip 人格一致，避免主对话人格分裂
- [x] 4.4 视需要微调 thinking 字幕文案，减少「诊疗」等医生腔（不改变节点逻辑）

## 5. 收尾与文档对齐

- [x] 5.1 更新路由/模块文件头注释，说明 tip↔clinic 共享 Python 会话与隐式飞轮主路径
- [x] 5.2 核对 Go 调用无需新字段（仅 device_no）；在 deploy 或相关说明中补充陪伴会话行为摘要（若已有文档提及诊疗人格则同步改口吻描述）
