## ADDED Requirements

### Requirement: Parent with no data SHALL try the most recent child once

When the spoken target is a parent event and the parent has no usable information, the system MUST try descendant events and MUST stop at the single descendant that has the most recent usable information. It MUST NOT continue after that hit, and MUST NOT pick an arbitrary catalog order. For history, usable information means history rows. For predict, usable information means a hot-path anchor or appointment next time, not an insufficient-sample message.

#### Scenario: Parent history falls through to latest child

- **WHEN** 用户查父事件且父侧没有历史行但其下某子事件有行
- **THEN** 系统 SHALL 用最近有记录的那个子事件作答
- **AND** MUST NOT 再试其余子事件

### Requirement: Child with no data SHALL try its parent once

When the spoken target is a child event and the child has no usable information, the system MUST retry once using that child's parent and MUST NOT walk sibling events. If the parent also has no usable information, the system MUST continue the existing miss or fallback path. Kin retries MUST NOT by themselves write a miss-inbox record.

#### Scenario: Formula predict uses feeding parent anchor

- **WHEN** 用户问配方奶下次时间且子事件没有锚点但其父事件喂养有可用预计锚点
- **THEN** 系统 SHALL 用父事件锚点作答
- **AND** MUST NOT 仅因子事件未命中就进入样本不足或估不准兜底
