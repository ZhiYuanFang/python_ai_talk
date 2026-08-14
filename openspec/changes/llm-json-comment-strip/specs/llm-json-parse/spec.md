## ADDED Requirements

### Requirement: LLM JSON 去注释后再解析
系统 SHALL 提供共享工具，将 LLM 返回的类 JSON 文本在 `json.loads` 之前去除注释。系统 MUST 支持去除字符串外的 `//` 行注释与 `/* */` 块注释。系统 MUST NOT 删除 JSON 字符串字面量内部的 `//`、`/*` 或 `#` 字符序列（例如 URL `http://`）。去注释后文本仍无法解析为 JSON 时，系统 MUST 按各调用方既有失败/降级策略处理，MUST NOT 假装解析成功。

#### Scenario: 行注释可解析
- **WHEN** LLM 返回含字符串外 `//` 说明的对象文本，其余为合法 JSON 结构
- **THEN** 共享解析 MUST 成功得到对应对象
- **AND** SHALL NOT 因该行注释单独失败

#### Scenario: 字符串内双斜杠保留
- **WHEN** JSON 某字符串字段值为含 `http://` 的 URL
- **THEN** 去注释后该字段值 MUST 仍含 `http://`
- **AND** 解析 MUST 成功

#### Scenario: 去注释后仍非法则降级
- **WHEN** 去注释后文本仍不是合法 JSON
- **THEN** 解析 MUST 失败并交由调用方降级
- **AND** MUST NOT 返回虚构的成功对象冒充模型结果

### Requirement: 解析前统一清洗管线
共享 LLM JSON 加载入口 SHALL 按顺序：去除首尾空白与 markdown 代码围栏（若有）→ 去注释 → `json.loads`（实现上可先抠顶层对象再 loads）。解析成功后，系统 MAY 将对象再序列化为标准 JSON 仅用于日志或规范化，MUST NOT 把含注释的原文当作已解析结构继续使用。

#### Scenario: 围栏加注释仍可解析
- **WHEN** LLM 返回 \`\`\`json 围栏包裹且对象内有字符串外 `//` 注释
- **THEN** 共享加载 MUST 解析成功

### Requirement: 各 LLM JSON 解析点须接入共享工具
凡对 LLM 模型原文执行 JSON 解析以得到业务结构的路径，系统 SHOULD 使用上述共享工具，MUST NOT 仅依赖提示词「禁止注释」作为唯一防护。至少包括：意图分类结果解析、澄清 LLM JSON 解析、护理留意生成 JSON 解析，以及对 LLM 输出做 `json.loads` 的 shared judge 类节点。

#### Scenario: 意图分类接入
- **WHEN** `classify_intent` 解析分类 LLM 返回内容
- **THEN** 系统 SHALL 经共享去注释管线再 loads
- **AND** 仅含注释障碍的合法结构 MUST 能得到意图字典而非仅因注释落入解析失败闲聊

#### Scenario: 澄清与护理留意接入
- **WHEN** 澄清 LLM 或护理留意生成节点解析模型 JSON
- **THEN** 系统 SHALL 使用同一共享去注释能力（或调用同一入口）
