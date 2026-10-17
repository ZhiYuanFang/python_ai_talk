## Why

思考字幕已经去掉拉丁字母和一部分 JSON / markdown 符号。英文思考被削掉字母后，逗号、句点、括号、箭头还会留在字幕上，客户端会闪出一串英文标点。

## What Changes

- 在现有思考字幕剔除上，再去掉英文标点：`,` `.` `(` `)` `>`，以及同类 ASCII 符号（`-` `<` `;` `/` `\` `|` `=` `+` `~` `@` `%` `^` `&` `!` `?`）。
- 剔除后只剩空白或这些符号的增量不推送。
- 中文、数字、空白、`\r`、中文句界（`。！？`）与中文标点保留。
- 口播回答正文、意图终答 JSON、图节点固定中文编排字幕不经过这套剔除。

## Capabilities

### New Capabilities

- `thinking-subtitle-ascii-punct`: LLM 思考字幕在已有去字母规则之外，再去掉英文标点，避免字母滤掉后只剩符号

### Modified Capabilities

- （无）当前基线 `openspec/specs/v0.0.1.md` 未单独描述思考字幕字符集；进行中的 `strip-thinking-ascii` 只覆盖字母与 JSON / markdown 符号，本变更另立增量。

## Impact

- `app/shared/graphs/thinking_sentence_cr.py` 的剔除字符表与句界集合（英文 `.!?` 不再作为句界）。
- 凡经 `ThinkingSentenceCrRewriter` 的思考字幕（意图、查史、预测、漏答、诊疗、留意点、成长轨迹等）都会少这些英文符号。
- 对外回答 `content` 与编排字幕 `emit_thinking` 不变。
