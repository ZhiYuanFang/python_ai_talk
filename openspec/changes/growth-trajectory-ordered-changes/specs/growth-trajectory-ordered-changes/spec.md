## ADDED Requirements

### Requirement: Trajectory Markdown prioritizes ordered possible changes

成长轨迹最终 Markdown SHALL 以「未来 horizon 日内可能发生的变化」为主段，用有序编号列出可观察的可能变化（发展先后或可能性从高到低）。主段 MUST NOT 使用「第1天」「第2天」等日历日作为主要分节。注意事项与喂养相关段落 MAY 保留但 MUST NOT 喧宾夺主。面向家长的正文篇幅 SHALL 以约 400～600 字为导向（替换约 200 字硬顶）。

#### Scenario: Numbered ladder not calendar days

- **WHEN** generate 产出未来 7 天轨迹 Markdown
- **THEN** 主段包含至少 2 条有序编号的可能变化
- **AND** MUST NOT 以「第1天」「第2天」…作为主要分节标题或主结构

#### Scenario: Length guidance relaxed

- **WHEN** 读取成长轨迹 system 或 generate user 提示
- **THEN** 字数约束 SHALL 体现约 400～600 字量级
- **AND** MUST NOT 再以约 200 字作为唯一硬顶

### Requirement: Plan questions probe ability boundaries with free_text when needed

`plan_next` 的决策提示 SHALL 要求：在信息不清时优先补问当前能力边界与近期行为细节，以便支撑有序可能变化。`format=choice` 时 choices MUST 仍恰好 2 个中文选项；需要细挖时 SHALL 使用 `format=free_text`。

#### Scenario: Fine detail uses free_text

- **WHEN** plan 决定 ask 且需要家长描述具体能力（如扶站是否稳定）
- **THEN** 待问 MAY 为 free_text
- **AND** 若为 choice 则 choices 长度 MUST 为 2

### Requirement: Final free_text is mandatory before generate

成长轨迹在调用 generate 产出 Markdown 之前，SHALL 至少完成一次 `final_free_text`（家长自述兜底）。当 plan 判定信息已够（enough）但尚未完成末问时，系统 MUST 先进入 final free_text，MUST NOT 直接 generate。

#### Scenario: Early enough still asks final free_text

- **WHEN** structured 问答未满最大轮次且 plan 输出 enough，且 final_ask_done 为 false
- **THEN** 下一步 SHALL 为 final_free_text（或等价 final_ask 路由）
- **AND** MUST NOT 立即进入 generate

#### Scenario: After final free_text generate runs

- **WHEN** final_free_text 完成且 final_ask_done 为 true
- **THEN** 图 SHALL 进入 generate
