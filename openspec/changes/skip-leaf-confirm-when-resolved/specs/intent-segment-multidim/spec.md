## MODIFIED Requirements

### Requirement: 单事件零 LLM 多维拼装
当系统判定用户输入为单事件时，MUST 跳过分句 LLM 与满血结构化分类 LLM，MUST 将整句作为唯一段执行类型/事件/形态/量/时间多维解析并拼装意图结果。段内维级小 LLM 与明细备注小 LLM 可按需调用。拼装成功且无阻塞澄清时，意图结果的 `need_confirm` SHALL 为 false（或等价不触发 leaf_confirm），以便直接执行；MUST NOT 仅因拼装成功而默认 need_confirm=true。

#### Scenario: 短句记奶
- **WHEN** 用户输入「吃了120奶」且判定为单事件、槽位齐全
- **THEN** 系统 SHALL NOT 调用分句 LLM
- **AND** 拼装结果 SHALL 可直接落库而无需 leaf_confirm

#### Scenario: 单事件可走 EVENT 小 LLM 且直执行
- **WHEN** 用户输入「睡着了」类单事件经 EVENT 小 LLM 定事件且无阻塞
- **THEN** 系统 SHALL NOT 调用分句 LLM 或满血分类
- **AND** SHALL 允许直接执行而不因 llm 命中强制确认
