## ADDED Requirements

### Requirement: LLM 思考允许句级下一句首回车
在保留编排字幕段首 `\r` 与「本流/本段首次 LLM thinking 增量可段首 `\r`」既有约定的前提下，系统 MAY 且在实现本仓库句界策略时 SHALL 在「上一句已于句界结束之后的下一句开头」对 LLM thinking 增量前置 `\r`。系统 MUST NOT 将「后续 LLM thinking 增量一律禁止 `\r`」理解为禁止该句级下一句首标记。系统 MUST NOT 在句界字符后仅为分隔而追加 `\r`。

#### Scenario: 句级标记与首包开泡可并存
- **WHEN** 同一 SSE 请求中编排字幕已段首 `\r`，且 LLM reasoning 含两句以上
- **THEN** 第二句及以后各句开头 MAY/SHALL（按句界策略）带 `\r`
- **AND** 编排字幕行为 MUST 保持段首 `\r` 不变

#### Scenario: 非句界增量不加回车
- **WHEN** 某一 LLM thinking 增量位于同一句中间（上一输出未停在句界）
- **THEN** 系统 MUST NOT 仅为分隔而对该增量强制前置 `\r`
