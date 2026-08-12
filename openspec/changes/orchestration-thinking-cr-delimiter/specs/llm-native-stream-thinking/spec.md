## RENAMED Requirements

### Requirement: Orchestration thinking ends with newline
FROM: Orchestration thinking ends with newline
TO: Orchestration thinking ends with carriage return

## MODIFIED Requirements

### Requirement: Orchestration thinking ends with carriage return

Orchestration-stage thinking captions (including `emit_thinking` custom events and route-level captions such as `llm_start`) SHALL end with a trailing carriage return character (`\r`). If the source message is non-empty and does not already end with `\r`, the system MUST append `\r` before emitting. The system MUST NOT strip a trailing newline (`\n`) before appending `\r`; a caption that already ends with `\n` but not `\r` MUST become a string ending with `\n\r`. Idempotency is defined solely by whether the content already ends with `\r`.

#### Scenario: emit_thinking appends carriage return

- **WHEN** `emit_thinking` is called with content `"正在翻翻记录…"` (no trailing `\r`)
- **THEN** the custom stream payload `content` is `"正在翻翻记录…\r"`

#### Scenario: Already CR-terminated caption unchanged

- **WHEN** `emit_thinking` is called with content that already ends with `\r`
- **THEN** the system MUST NOT append an additional `\r`

#### Scenario: LF-only terminator still gets CR

- **WHEN** `emit_thinking` is called with content that ends with `\n` but not `\r`
- **THEN** the custom stream payload `content` MUST end with `\n\r`

### Requirement: LLM thinking does not append trailing newline

LLM streaming thinking increments forwarded from `LLMResponse.thinking` to SSE MUST be emitted as returned by the model mapping layer. The system MUST NOT append a trailing `\r` or `\n` to those increments solely for item-delimiter formatting.

#### Scenario: LLM thinking increment without forced delimiter

- **WHEN** a stream chunk yields `thinking="先看夜里喂养"` (no trailing `\r` or `\n`)
- **THEN** the SSE thinking `content` is exactly `"先看夜里喂养"` without an added trailing `\r` or `\n`
