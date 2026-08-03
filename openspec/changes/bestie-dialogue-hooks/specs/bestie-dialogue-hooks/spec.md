## ADDED Requirements

### Requirement: Guiding follow-up for two-way dialogue
Clinic and tip answer prompts SHALL instruct the model to end replies with a guiding follow-up when possible (open question or light either/or), including point-query and summary answers after the factual answer, so the parent can continue a real exchange rather than only receiving one-sided comfort.

#### Scenario: Advice prompt requires dialogue hook
- **WHEN** the clinic or tip system prompt is built
- **THEN** it includes guidance to append a guiding follow-up topic when possible

#### Scenario: Point-query still facts-first then guide
- **WHEN** the clinic system prompt describes point-query time answers
- **THEN** it requires stating injected record times first and still encourages a light guiding follow-up afterward

### Requirement: Same-age peer-parent simulation when months known
When baby age months are known, prompts SHALL allow a brief “if my child were this age, I might…” peer simulation. When months are unknown, prompts SHALL forbid inventing a same-age peer child. Peer simulation SHALL NOT be presented as the user’s feeding records or prior chat.

#### Scenario: Months known allows peer line
- **WHEN** clinic/tip prompts describe persona with known months available in context
- **THEN** they allow a short same-age peer-parent line as resonance

#### Scenario: Months unknown forbids fake same age
- **WHEN** age is unknown
- **THEN** prompts forbid assuming a same-age peer child

### Requirement: Approximately eighty character budget
Advice, chit-chat, and tip opener prompts SHALL target roughly 80 Chinese characters (replacing the prior ~50 target). Point-query and summary MAY run slightly longer only as needed to state times/trends clearly, while still aiming near 80.

#### Scenario: Length target updated in prompts
- **WHEN** clinic and tip system prompts state length guidance for non-lookup or opener replies
- **THEN** they reference approximately 80 characters rather than 50

### Requirement: Grounded and safety rules retained
Prompts SHALL retain grounded citation rules (cite chat/history when present; do not fabricate memory when absent) and safety rules (no diagnosis, no drug doses/prescriptions).

#### Scenario: No fabricated memory still present
- **WHEN** neither chat nor history is available
- **THEN** prompts still forbid inventing “last time” or “records show” about the user’s baby
