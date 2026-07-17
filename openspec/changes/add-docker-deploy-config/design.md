# Design: Docker 多环境部署配置

## Context

当前项目采用单一 `docker-compose.yml` 配置，所有环境变量直接写在文件中。这种方式存在以下问题：

1. **环境耦合**：无法区分本地、测试、生产环境的差异配置
2. **密钥暴露风险**：敏感信息直接写在 compose 文件中
3. **端口冲突**：同机部署多套环境时端口冲突
4. **镜像管理混乱**：无明确的镜像仓库隔离策略

兄弟仓 go_ai_talk 已建立成熟的多环境部署体系，采用 overlay 组合模式：

```
基线 (docker-compose.microservices.yml)
  ├── 定义服务骨架（服务名、镜像构建、环境变量骨架）
  └── 引用 ${VAR} 占位符

Overlay (docker-compose.*.yml)
  ├── 只改：镜像、端口、网络、container_name
  └── 不写：environment（全部由 .env.* 注入）

环境变量 (.env.*)
  └── 完整定义所有环境变量值
```

## Goals / Non-Goals

**Goals:**

1. 建立 local/test/prod 三套环境的标准化配置分离
2. 实现与 go_ai_talk 一致的部署模式，降低学习成本
3. 提供面向新手的部署指南文档，涵盖从零开始的所有步骤
4. 确保测试/生产环境的项目名、端口、镜像仓库隔离

**Non-Goals:**

1. 不涉及 CI/CD 流程改造（已由 GitHub Actions 处理）
2. 不涉及应用代码改动
3. 不涉及 Kubernetes 配置（保持 Docker Compose 范围）

## Decisions

### D1: 采用 Overlay 组合模式

**决定**：将 docker-compose.yml 改为基线配置，新增 .local/.test/.prod overlay 文件。

**备选方案：**
- 方案 A：三套独立 docker-compose 文件 → 拒绝，维护成本高，重复多
- 方案 B：单文件 + profile 区分 → 拒绝，环境变量隔离不清晰
- 方案 C：Overlay 组合模式（与 go_ai_talk 一致）→ 采用

**理由**：
- 复用兄弟仓成熟方案，降低团队认知负担
- 基线定义公共部分，overlay 只改差异点
- 环境变量完全分离，便于安全管理和密钥轮换

### D2: 环境变量文件位置

**决定**：放置在 `env/.env.*` 目录下，与 go_ai_talk 的 `manifest/docker/env/` 结构对齐。

**理由**：
- 集中管理，便于查找和审计
- 便于 .gitignore 统一排除敏感文件
- 与兄弟仓目录结构一致

### D3: 端口分配策略

**决定**：
| 环境 | 端口 | 说明 |
|------|------|------|
| local | 8000 | 本地开发 |
| test | 18000 | 测试环境，避免与生产冲突 |
| prod | 8000 | 生产环境 |

**理由**：
- 遵循 go_ai_talk 的 19xxx 测试端口约定
- 生产环境使用标准端口

### D4: 镜像仓库隔离

**决定**：复用 go_ai_talk 的 ACR 仓库，不单独创建。

| 环境 | 仓库地址 |
|------|----------|
| test | `crpi-lff3xynwzvqxxxjk-vpc.cn-hangzhou.personal.cr.aliyuncs.com/pangbao-test` |
| prod | `crpi-lff3xynwzvqxxxjk-vpc.cn-hangzhou.personal.cr.aliyuncs.com/pangbao-release` |

**理由**：
- 共享 ACR 账号，减少运维成本
- python-ai-talk 作为 go_ai_talk 的子服务，统一管理更合理

### D5: Redis 配置差异

**决定**：
| 环境 | Redis 配置 |
|------|------------|
| local | `redis://localhost:6379/0` 或 cluster |
| test | `redis-test:6379` 单节点 |
| prod | `redis-node-1:7001,redis-node-2:7002,redis-node-3:7003` cluster |

**理由**：
- 与 go_ai_talk 保持一致
- 测试环境简化为单节点，降低资源消耗

### D6: 服务发现地址

**决定**：
| 环境 | 服务发现方式 |
|------|--------------|
| local | `host.docker.internal:9801/9802/9803` |
| test | `history-service:9801` 等服务名 |
| prod | `history-service:9801` 等服务名 |

**理由**：
- 本地开发通过 host.docker.internal 访问宿主机
- 测试/生产通过 Docker 网络服务名访问

## Risks / Trade-offs

### R1: 敏感信息泄露风险

**风险**：.env.* 文件包含 API Key 等敏感信息，误提交到 Git 将导致泄露。

**缓解措施**：
- `env/.env.local`、`env/.env.test`、`env/.env.prod` 加入 `.gitignore`
- 提供 `env/.env.example` 作为模板，不含真实密钥
- 生产密钥考虑使用 GitHub Secrets 注入

### R2: 新手学习成本

**风险**：Docker Compose overlay 模式对新手不直观，可能造成困惑。

**缓解措施**：
- 部署指南文档提供完整命令示例，可直接复制粘贴
- 文档包含目录结构说明和原理讲解
- 提供常见问题解答章节

### R3: 与 go_ai_talk 配置不同步

**风险**：go_ai_talk 更新配置后，python_ai_talk 未同步更新。

**缓解措施**：
- 部署指南文档说明配置来源
- 定期与兄弟仓对齐配置

## Migration Plan

### 阶段 1：创建配置文件

1. 创建 `docker-compose.local.yml`、`docker-compose.test.yml`、`docker-compose.prod.yml`
2. 重构 `docker-compose.yml` 为基线配置
3. 创建 `env/.env.local`、`env/.env.test`、`env/.env.prod`
4. 创建 `docs/deploy-guide.md`

### 阶段 2：验证部署

1. 本地验证：`docker compose --env-file env/.env.local -f docker-compose.yml -f docker-compose.local.yml up -d --build`
2. 测试环境验证：推送镜像后启动测试栈
3. 生产环境验证：灰度发布验证

### 回滚策略

如遇问题，可临时回退到原有单一 `docker-compose.yml` 配置（保留备份）。

## Open Questions

1. **是否需要配置健康检查超时参数差异化？**
   - 测试环境可能需要更长的启动等待时间
   - 建议：先用默认值，后续按需调整

2. **是否需要配置资源限制（CPU/内存）？**
   - 生产环境可能需要限制资源使用
   - 建议：暂不配置，后续按需添加