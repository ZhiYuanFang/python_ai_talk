## ADDED Requirements

### Requirement: Native thinking mode on stream when enabled

When `llm_client.stream` is called with `thinking_enabled=True` for provider `deepseek` or `glm` (including alias `zhipu`), the system SHALL enable the provider's native thinking/reasoning mode on that request (for example via `extra_body` thinking enabled). When `thinking_enabled=False`, the system MUST NOT enable native thinking mode for that stream call. Shared cached clients used by `invoke` MUST NOT permanently carry thinking-enabled configuration from a prior stream call.

#### Scenario: Stream enables native thinking for DeepSeek

- **WHEN** a caller invokes `stream` with `thinking_enabled=True` and provider `deepseek`
- **THEN** the outbound request includes the provider thinking-enabled parameter

#### Scenario: Invoke is unaffected by stream thinking cache

- **WHEN** a stream call with thinking enabled completes and a later `invoke` uses the same provider and model
- **THEN** that invoke request MUST NOT include thinking-enabled solely due to client cache reuse

### Requirement: Map reasoning_content to LLMResponse.thinking

During streaming with `thinking_enabled=True`, the system SHALL map provider reasoning deltas (including `reasoning_content` or equivalent exposed on the chunk) to `LLMResponse.thinking`, and map answer text deltas to `LLMResponse.content`. A single chunk MAY yield both non-empty `thinking` and non-empty `content`. The system MUST NOT rely on parsing `[思考]` or `思考：` markers inside `content` as the primary mechanism for filling `thinking`.

#### Scenario: Reasoning delta becomes thinking

- **WHEN** a stream chunk contains non-empty reasoning content and empty or absent answer content
- **THEN** the yielded `LLMResponse` has `thinking` equal to that reasoning text and `content` empty (or empty string)

#### Scenario: Answer delta becomes content

- **WHEN** a stream chunk contains non-empty answer content and no reasoning
- **THEN** the yielded `LLMResponse` has `content` equal to that answer text and `thinking` empty

#### Scenario: Mixed chunk

- **WHEN** a stream chunk contains both reasoning and answer content
- **THEN** both fields are populated on the yielded `LLMResponse` without dropping either side

### Requirement: Orchestration thinking ends with newline

Orchestration-stage thinking captions (including `emit_thinking` custom events and route-level captions such as `llm_start`) SHALL end with a trailing newline character. If the source message is non-empty and does not already end with `\n`, the system MUST append `\n` before emitting.

#### Scenario: emit_thinking appends newline

- **WHEN** `emit_thinking` is called with content `"正在翻翻记录…"` (no trailing newline)
- **THEN** the custom stream payload `content` is `"正在翻翻记录…\n"`

#### Scenario: Already terminated caption unchanged

- **WHEN** `emit_thinking` is called with content that already ends with `\n`
- **THEN** the system MUST NOT append an additional `\n`

### Requirement: LLM thinking does not append trailing newline

LLM streaming thinking increments forwarded from `LLMResponse.thinking` to SSE MUST be emitted as returned by the model mapping layer. The system MUST NOT append a trailing `\n` to those increments solely for formatting.

#### Scenario: LLM thinking increment without forced newline

- **WHEN** a stream chunk yields `thinking="先看夜里喂养"` (no trailing newline)
- **THEN** the SSE thinking `content` is exactly `"先看夜里喂养"` without an added trailing `\n`
