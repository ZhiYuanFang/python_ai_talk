## MODIFIED Requirements

### Requirement: Experienced bestie tone in companion prompts
Clinic answer prompts (and tip openers using the same product surface) SHALL instruct the model to reply as a parenting expert: clear, warm, grounded, non-clinical, without calling itself a doctor or pediatric assistant, and without a bestie-companion persona as the primary role.

#### Scenario: System prompt encodes persona
- **WHEN** the clinic answer system prompt is built
- **THEN** it includes guidance for parenting-expert tone and forbids doctor/assistant self-identification

### Requirement: Ground replies in chat and feeding history when present
When feeding history is present, the prompts SHALL require the reply to cite one relevant history fact (time, count, or interval) and then respond accordingly. When recent companion chat context is present in the user message, the prompts MAY allow using it as soft background and MUST NOT require the reply to reference the prior turn before answering. Prompts SHALL NOT describe feeding history as optional background-only for advice/chit-chat when history is injected.

#### Scenario: Chat context present
- **WHEN** `chat_context` is non-empty in the clinic (or tip) user message builder
- **THEN** the closing instruction does not require naming or clearly alluding to the prior conversation before answering

#### Scenario: Feeding history present
- **WHEN** feeding history is injected into the clinic (or tip) user message
- **THEN** the closing instruction requires citing one relevant history fact in the reply

#### Scenario: Both present
- **WHEN** both chat context and feeding history are injected
- **THEN** prompts require citing history and may optionally use chat as background without inventing facts
