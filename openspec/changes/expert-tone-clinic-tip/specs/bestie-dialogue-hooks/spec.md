## MODIFIED Requirements

### Requirement: Guiding follow-up for two-way dialogue
Clinic and tip answer prompts SHALL NOT hard-require ending every reply with a guiding follow-up (open question or light either/or) as a bestie dialogue hook. Prompts MAY omit dialogue-hook instructions entirely. Point-query and summary answers SHALL still state injected record facts first when history is used.

#### Scenario: Advice prompt requires dialogue hook
- **WHEN** the clinic or tip system prompt is built
- **THEN** it does not mandate appending a guiding follow-up topic

#### Scenario: Point-query still facts-first then guide
- **WHEN** the clinic system prompt describes point-query time answers
- **THEN** it requires stating injected record times first
- **AND** it does not require a light guiding follow-up afterward

### Requirement: Same-age peer-parent simulation when months known
Clinic and tip prompts SHALL NOT require a “if my child were this age…” peer-parent simulation line. When months are unknown, prompts SHALL still forbid inventing a same-age peer child. Baby age MAY still appear in the user message as factual context for the expert answer.

#### Scenario: Months known allows peer line
- **WHEN** clinic/tip prompts describe persona with known months available in context
- **THEN** they do not require a same-age peer-parent resonance line

#### Scenario: Months unknown forbids fake same age
- **WHEN** age is unknown
- **THEN** prompts forbid assuming a same-age peer child

### Requirement: Grounded and safety rules retained
Prompts SHALL retain feeding-history citation when history is injected, SHALL NOT require chat citation when chat is injected, SHALL forbid fabricated memory when evidence is absent, and SHALL retain safety rules (no diagnosis, no drug doses/prescriptions, no decisive medical claims).

#### Scenario: No fabricated memory still present
- **WHEN** neither chat nor history is available
- **THEN** prompts still forbid inventing “last time” or “records show” about the user’s baby
