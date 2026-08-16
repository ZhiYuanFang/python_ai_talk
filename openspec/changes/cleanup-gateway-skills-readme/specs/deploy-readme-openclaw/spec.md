## ADDED Requirements

### Requirement: README 以 LangGraph→OpenClaw 部署对照为主

仓库 `README.md` MUST 用简短对照说明：以前只需启动 Python（LangGraph 智能体入口），现在必须先启动 OpenClaw Gateway，Python 仅 tools/知识库，Go 改打 Gateway。README MUST NOT 以冗长云主机入门或过期的 `/v1/analyze/*` API 文档作为主内容。

#### Scenario: 对照表存在

- **WHEN** 读者打开 README 部署相关章节
- **THEN** MUST 能看到旧（只起 Python）与新（Gateway + Python tools + Go）的差异表或等价条目
- **AND** MUST 给出 Gateway 启动与 `/v1/models`（或等价）最短验收命令

#### Scenario: 禁止误导旧入口

- **WHEN** README 描述本仓 HTTP
- **THEN** MUST NOT 将 `/v1/analyze/intent`、`/v1/clinic`、tip 列为现行产品入口
- **AND** MUST 指向 `/v1/tools/*` 与 `/v1/health`（及知识库）为 Python 现行面

### Requirement: 过期部署文档不得与 README 抢权威

若 `docs/deploy-guide.md` 仍含 LangGraph/确认流/意图流式等旧说明，MUST 在文首标明「部署以 README 为准」或删除冲突章节，避免双源。

#### Scenario: 文首声明

- **WHEN** 打开过期的 deploy-guide
- **THEN** 文首 MUST 指向 README 为现行部署权威，或该文件已移除冲突的旧智能体部署步骤
