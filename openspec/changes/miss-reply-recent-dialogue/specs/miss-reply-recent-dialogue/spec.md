## ADDED Requirements

### Requirement: Intent SHALL keep a ten-minute spoken dialogue window

After an intent turn produces a non-empty outward reply, the system MUST append that turn for the device: the parent utterance, the reply actually spoken, and a timestamp. Confirm prompts and persist receipts MUST be included. When the outward reply is a miss soft reply, the stored assistant text MUST be that soft reply, not the internal hard text. Empty replies MUST NOT be stored. The window MUST drop turns older than 10 minutes. This store MUST be separate from the clinic companion session. A storage failure MUST NOT block the intent reply. The dialogue MUST NOT be written to the event-phrase flywheel or treated as feeding records.

意图侧 MUST 按设备保留最近 10 分钟家长听到的来回，与诊疗陪伴会话分开。

#### Scenario: Spoken miss reply is what gets stored

- **WHEN** 本轮对外念的是漏答自由回答
- **THEN** 记录中的回答 MUST 是该自由回答，MUST NOT 是内部硬文案

#### Scenario: Quiet device drops old turns

- **WHEN** 上一轮早于 10 分钟
- **THEN** 再次读取时 MUST NOT 再包含该轮

### Requirement: Miss soft reply SHALL inject recent dialogue within a length budget

When building the miss soft-reply prompt, the system MUST include prior turns from the ten-minute window that fit in about 800 characters, newest turns first. Older turns that do not fit MUST be omitted. A single over-long side of a turn MUST be shortened to a prefix. The current utterance MUST remain its own line and MUST NOT be duplicated as a prior turn. If no prior turn fits, the prompt MUST omit the dialogue block and MUST still include the utterance, baby profile, and predict snapshot as it does today. The prompt MUST tell the model the dialogue is background only and MUST NOT treat it as feeding records. LLM failure MUST still fall back to the hard text.

漏答自由回答 MUST 注入放得下的近况。约 800 字放不下时 MUST 丢掉更早的轮。没有近况时 MUST 仍按原话、画像和快照回答。

#### Scenario: Budget drops older turns

- **WHEN** 10 分钟内的来回拼在一起超过约 800 字
- **THEN** 提示词 MUST 保留较新的轮，MUST 可以不包含更早的轮，且 MUST 仍包含当前原话与预测快照

#### Scenario: Empty window

- **WHEN** 该设备 10 分钟内没有更早的来回
- **THEN** 提示词 MUST NOT 出现近况段，回答输入仍包含原话、宝宝画像和预测快照
