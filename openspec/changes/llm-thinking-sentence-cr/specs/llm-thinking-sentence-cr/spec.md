## ADDED Requirements

### Requirement: LLM 思考按句在下一句首加回车
当系统向外透出 LLM 原生 reasoning 流式增量时，系统 SHALL 检测句界字符（中文 `。！？` 与英文 `.!?`）。当上一句已在句界处结束后，系统 SHALL 在**下一句**输出内容的开头前置一个 `\r`。系统 MUST NOT 在句界字符之后直接拼接 `\r`（以免流结束时客户端清空最后一句字幕）。系统 MUST NOT 对每个 token/增量一律加 `\r`。

#### Scenario: 第二句开头带回车
- **WHEN** reasoning 先后产出「先判断是否预测。」与「再对齐事件名」
- **THEN** 含「再对齐」的那次透出内容 SHALL 以 `\r` 开头（或该句正文前紧接 `\r`）
- **AND** 「。」之后 MUST NOT 单独或紧随发出仅用于清空的 `\r`

#### Scenario: 流结束不发裸回车
- **WHEN** reasoning 以句界字符结束且之后无更多正文
- **THEN** 系统 MUST NOT 再发送仅含 `\r` 或句末后多余 `\r` 的 thinking 事件导致字幕被清空

### Requirement: 覆盖全部 agent 的 LLM 思考出口
feeding intent、clinic、care-alert、growth-trajectory 等对外 SSE 路径上，凡将 LLM reasoning 映射为 `type=thinking` 的流式出口，SHALL 应用同一套句界「下一句首 `\r`」处理。编排节点字幕（非 LLM reasoning）不在本要求强制改写范围内。

#### Scenario: 共用出口一致
- **WHEN** intent 图内维 LLM 与 clinic 主答 LLM 均产生多句 reasoning
- **THEN** 两处 SHALL 均在上一句结束后的下一句开头前置 `\r`
