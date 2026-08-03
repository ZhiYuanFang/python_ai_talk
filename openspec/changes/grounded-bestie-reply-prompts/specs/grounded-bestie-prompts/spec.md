## ADDED Requirements

### Requirement: Experienced bestie tone in companion prompts
Clinic answer prompts (and tip openers using the same persona) SHALL instruct the model to reply as an experienced parenting bestie: warm, grounded, non-clinical, without calling itself a doctor or pediatric assistant.

#### Scenario: System prompt encodes persona
- **WHEN** the clinic answer system prompt is built
- **THEN** it includes guidance for experienced-bestie tone and forbids doctor/assistant self-identification

### Requirement: Ground replies in chat and feeding history when present
When recent companion chat context is present in the user message, the prompts SHALL require the reply to reference the prior turn before answering the current question. When feeding history is present, the prompts SHALL require the reply to cite one relevant history fact (time, count, or interval) and then respond accordingly. Prompts SHALL NOT describe feeding history as optional background-only for advice/chit-chat when history is injected.

#### Scenario: Chat context present
- **WHEN** `chat_context` is non-empty in the clinic (or tip) user message builder
- **THEN** the closing instruction requires naming or clearly alluding to the prior conversation before answering

#### Scenario: Feeding history present
- **WHEN** feeding history is injected into the clinic (or tip) user message
- **THEN** the closing instruction requires citing one relevant history fact in the reply

#### Scenario: Both present
- **WHEN** both chat context and feeding history are injected
- **THEN** prompts require weaving both into a short grounded reply without inventing facts

### Requirement: No fabricated memory when no evidence
When neither recent chat context nor feeding history is available, prompts SHALL forbid fabricating phrases like “last time you said” or “the records show”, while still allowing a short honest companion reply.

#### Scenario: No chat and no history
- **WHEN** the user message has empty/absent chat context and empty/absent feeding history
- **THEN** closing instructions forbid inventing prior-chat or record citations

### Requirement: Short reply budget for advice and openers
For advice/chit-chat and tip openers, prompts SHALL target roughly 50 Chinese characters. Point-query and summary clinic answers MAY be slightly longer when needed to state injected readable times or trends accurately.

#### Scenario: Advice length guidance
- **WHEN** the clinic system prompt describes non-lookup advice replies
- **THEN** it includes an approximately 50-character length target and instructs selecting at most one grounding fact

### Requirement: Safety rules retained
Prompts SHALL continue to forbid diagnosis, drug doses, and prescriptions, and SHALL keep point-query and summary rules that require using injected feeding records without fabricating times.

#### Scenario: Point query still record-bound
- **WHEN** the question is a time/last-event lookup
- **THEN** prompts still require answering from injected readable record times
