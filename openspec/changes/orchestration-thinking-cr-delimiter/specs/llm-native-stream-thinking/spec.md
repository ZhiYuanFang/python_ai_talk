## RENAMED Requirements

### Requirement: Orchestration thinking ends with newline
FROM: Orchestration thinking ends with newline
TO: Thinking segment starts with carriage return

## MODIFIED Requirements

### Requirement: Thinking segment starts with carriage return

Orchestration-stage thinking captions (including `emit_thinking` custom events and route-level captions such as `llm_start`) SHALL begin with a leading carriage return character (`\r`). If the source message is non-empty and does not already start with `\r`, the system MUST prepend `\r` before emitting. Idempotency is defined solely by whether the content already starts with `\r`.

Additionally, when clinic or tip SSE forwards LLM streaming thinking increments, the **first** non-empty `thinking` increment in that stream MUST likewise begin with `\r` (prepend if missing). Subsequent thinking increments in the same stream MUST be forwarded without adding a leading `\r` solely for segment marking.

#### Scenario: emit_thinking prepends carriage return

- **WHEN** `emit_thinking` is called with content `"正在翻翻记录…"` (no leading `\r`)
- **THEN** the custom stream payload `content` is `"\r正在翻翻记录…"`

#### Scenario: Already CR-prefixed caption unchanged

- **WHEN** `emit_thinking` is called with content that already starts with `\r`
- **THEN** the system MUST NOT prepend an additional `\r`

#### Scenario: First LLM thinking increment opens a segment

- **WHEN** the first non-empty LLM thinking increment in a clinic or tip stream is `"先看夜里喂养"` (no leading `\r`)
- **THEN** the SSE thinking `content` is `"\r先看夜里喂养"`

#### Scenario: Later LLM thinking increments unchanged

- **WHEN** a later LLM thinking increment in the same stream is `"再补一句"` (no leading `\r`)
- **THEN** the SSE thinking `content` is exactly `"再补一句"` without an added leading `\r`

### Requirement: LLM thinking does not append trailing newline

LLM streaming thinking increments forwarded from `LLMResponse.thinking` to SSE MUST NOT receive a trailing `\r` or `\n` solely for item-delimiter formatting. Leading `\r` is allowed only for the first non-empty thinking increment as required by "Thinking segment starts with carriage return".

#### Scenario: LLM thinking increment without forced trailing delimiter

- **WHEN** a stream chunk yields `thinking="先看夜里喂养"` as a non-first increment (or after leading `\r` has already been applied for the first increment)
- **THEN** the system MUST NOT append a trailing `\r` or `\n` for delimiter purposes
