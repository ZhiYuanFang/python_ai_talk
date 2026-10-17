## Why

LLM 思考流里常夹着 JSON 字段名、markdown 标记和其它英文字符，直接推给客户端会显得很怪。思考字幕本来就是快速闪过，缺几个字没关系，展示前去掉这些字符即可。

## What Changes

- 在共用思考管道里，对即将推给客户端的 LLM reasoning 增量去掉英文字母，以及常见的 JSON / markdown 格式符号。
- 只动思考字幕，不动回答正文，也不动图节点开头的固定中文编排字幕。
- 所有经 `stream_llm_collect` 透出思考的路径一并生效，不按意图、诊疗等智能体单独开关。

## Capabilities

### New Capabilities

- `thinking-display-strip-ascii`: 对外 thinking SSE 中，LLM reasoning 增量不得保留英文字母与常见格式符号

### Modified Capabilities

- （无）当前基线未单独描述思考字幕字符集。

## Impact

- `app/shared/graphs/thinking_sentence_cr.py` 或紧邻的共用过滤：在句界改写前后统一剔除
- `app/shared/graphs/stream_llm_collect.py`：继续作为唯一透出入口，不新增各模块调用
- 意图、查史、预测、漏答、诊疗、留意点、成长轨迹等凡走该管道的思考字幕都会变干净
