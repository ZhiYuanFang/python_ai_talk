## Why

pending 澄清续聊目前只靠硬字符串白名单解析肯定/拒绝词；复合句（如「是的，喂了30毫升」「不是的，是母乳」）以及带句末标点的「是的。」会被当成答非所问并清 pending，丢掉正在确认的事件语境。需要在硬匹配之后增加带 pending 语境的 LLM 解析，并修正硬匹配归一化。

## What Changes

- 硬匹配前对用户回复做轻量归一化（去首尾空白、剥句末 `。．.!！?？`、英文大小写折叠）
- 硬匹配 miss 后调用 LLM 澄清解析（注入 pending kind / 问句 / options / 原话），输出结构化动作，而非一律 OFF_TOPIC
- 支持复合回复动作：`confirm`（可带 quantity 覆盖 pending）、`select`、`correct`、`reject`、`new_intent`、`ask_again`
- `correct` 到用户点名的**叶子**事件：清旧 pending 并**直接落地**；若为父事件：再走父消歧；飞轮在最终叶子落地时写**消歧前原话**，不对旧错误向量 `success_count++`
- LLM 超时或坏 JSON：保持 pending，返回 `ask_again`（不清 pending）
- 保留硬匹配快路径；LLM 判为 `new_intent` 时仍清 pending 并冷启动（逃逸口）

## Capabilities

### New Capabilities

- `pending-reply-resolution`: pending 续聊自由文本的分层解析（归一化硬匹配 + LLM 澄清兜底）、复合句动作语义、correct 落地规则与飞轮写入约定

### Modified Capabilities

- （无主线 `openspec/specs/` 存量；行为上延伸 `parent-event-disambiguation` 的「其余一律新意图」规则：硬匹配 miss 后先 LLM，仅当 LLM 判定离题或显式 `new_intent` 时才当新意图）

## Impact

- `app/feeding/services/clarification.py`：归一化、扩展 `ResolveResult`、接入 LLM 解析
- `app/feeding/services/intent_pipeline.py`：处理 confirm/select/correct 的 quantity 覆盖、correct 后父校验/叶子直落、飞轮
- 新增澄清解析 prompt（可放 `app/feeding/graphs/nodes/prompts/` 或 services 侧）
- 复用现有 `llm_client`；`/intent` 契约不变（仍靠 `conversation_id` 续聊）
- 延迟：硬匹配 miss 时多一次 LLM 调用；失败时用户多看到一轮再问
