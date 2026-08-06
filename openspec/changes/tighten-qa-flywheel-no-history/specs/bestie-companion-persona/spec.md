## MODIFIED Requirements

### Requirement: Ground replies in chat and feeding history when present
For **clinic** answer generation when `needs_history` is true (or history is forced), when recent companion chat context is present in the user message, the prompts SHALL require the reply to reference the prior turn before answering the current question; when feeding history is present, the prompts SHALL require the reply to cite one relevant history fact (time, count, or interval) and then respond accordingly. Prompts SHALL NOT describe feeding history as optional background-only for advice/chit-chat when history is injected under that mode.

For **clinic** answer generation when `needs_history` is false and history is not forced, prompts SHALL NOT require citing companion chat or feeding history, even if such data exists elsewhere in session state.

For **tip** openers, when chat context or feeding history is injected, existing citation requirements remain unchanged by this capability delta.

#### Scenario: Chat context present on history-needed clinic path
- **WHEN** clinic `needs_history` is true and `chat_context` is non-empty in the clinic user message builder
- **THEN** the closing instruction requires naming or clearly alluding to the prior conversation before answering

#### Scenario: Feeding history present on history-needed clinic path
- **WHEN** clinic `needs_history` is true and feeding history is injected into the clinic user message
- **THEN** the closing instruction requires citing one relevant history fact in the reply

#### Scenario: Both present on history-needed clinic path
- **WHEN** clinic `needs_history` is true and both chat context and feeding history are injected
- **THEN** prompts require weaving both into a short grounded reply without inventing facts

#### Scenario: Tip still grounds when evidence injected
- **WHEN** tip user message builder injects non-empty chat context or feeding history
- **THEN** tip closing instructions still require the corresponding citation behavior

## ADDED Requirements

### Requirement: Clinic no-history path forbids memory citation instructions
When clinic generates with `needs_history=false` (and not force-needs-history), system and closing prompts SHALL forbid instructing the model to cite “上次你说” / 喂养记录类依据，and the user message SHALL omit feeding-history and chat-context grounding blocks so answers remain globally reusable for Q&A promotion.

#### Scenario: No-history clinic prompt omits citation mandates
- **WHEN** clinic answer prompts are built with `needs_history=false`
- **THEN** they do not include hard requirements to name prior chat or feeding records
- **AND** they still forbid fabricating such citations

### Requirement: Clinic no-history path solicits user affirmation
When clinic generates with `needs_history=false` (and not force-needs-history), system and closing prompts SHALL require the reply to end with a short, colloquial ask whether the parent finds this response right/useful (so they can accept or reject for the implicit flywheel). The ask SHALL NOT be a formal survey or rating request.

#### Scenario: No-history closing asks for affirmation
- **WHEN** clinic answer prompts are built with `needs_history=false`
- **THEN** closing instructions require lightly asking if the parent affirms the reply
- **AND** history-needed clinic prompts are not required to use this affirmation closing
