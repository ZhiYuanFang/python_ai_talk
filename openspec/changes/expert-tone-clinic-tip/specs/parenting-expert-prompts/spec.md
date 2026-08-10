## ADDED Requirements

### Requirement: Parenting expert persona for clinic and tip
Clinic and tip answer system prompts SHALL position the model as a parenting expert speaking to the parent: clear, warm, and restrained. Prompts SHALL NOT use a “闺蜜 / bestie companion” persona as the primary role, SHALL NOT require bestie-style emotional scripts or mandatory same-age peer lines (“我家要是这月龄…”), and SHALL NOT self-identify as a doctor or pediatric clinical assistant.

#### Scenario: Clinic system prompt is expert-oriented
- **WHEN** the clinic answer system prompt is built (needs_history true or false)
- **THEN** it describes a parenting-expert role to the parent
- **AND** it does not primarily require a bestie companion persona

#### Scenario: Tip system prompt is expert-oriented
- **WHEN** the tip answer system prompt is built
- **THEN** it describes a parenting-expert opener tone for the recorded event
- **AND** it does not primarily require a bestie companion persona

### Requirement: Cite feeding history when injected; chat optional
When feeding history is injected into the clinic or tip user message, prompts SHALL require the reply to cite one relevant history fact (time, count, or interval) before or within the answer. When companion `chat_context` is present, prompts MAY allow using it as background and MUST NOT require naming or alluding to a prior chat turn. Prompts SHALL forbid fabricating “上次你说” or “记录里” when the corresponding evidence is absent.

#### Scenario: Feeding history present requires citation
- **WHEN** feeding history is injected into the clinic or tip user message
- **THEN** closing or system guidance requires citing one relevant history fact

#### Scenario: Chat context present does not require citation
- **WHEN** `chat_context` is non-empty and feeding history may or may not be present
- **THEN** prompts do not require mandatory citation of the prior conversation
- **AND** prompts still forbid inventing prior-chat content that was not provided

#### Scenario: Neither present forbids fabricated memory
- **WHEN** chat context and feeding history are both absent/empty
- **THEN** prompts forbid inventing prior-chat or record citations

### Requirement: No solicitation of affirmation
Clinic and tip prompts SHALL NOT instruct the model to end with a request for the parent to affirm usefulness or correctness (e.g. 「说得对吗」「有用吗」「认不认」) for implicit-feedback harvesting or dialogue closure.

#### Scenario: No-history clinic path has no affirmation ask
- **WHEN** clinic prompts are built with `needs_history=false`
- **THEN** closing instructions do not require soliciting parent affirmation

#### Scenario: Tip opener has no affirmation ask
- **WHEN** the tip answer prompt closing is built
- **THEN** it does not require soliciting parent affirmation

### Requirement: Non-decisive medical safety
Prompts SHALL forbid disease diagnosis, drug doses, and prescriptions, and SHALL avoid decisive medical conclusions. When the parent appears worried about health, prompts SHALL allow a gentle suggestion to consult a clinician without alarmist wording.

#### Scenario: Safety bounds in expert prompts
- **WHEN** clinic or tip system prompts are built
- **THEN** they include no-diagnosis / no-prescription constraints and non-alarmist medical deferral
