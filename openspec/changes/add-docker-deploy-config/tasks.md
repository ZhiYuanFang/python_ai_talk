# Tasks: Docker 多环境部署配置

## 1. Docker Compose Overlay 文件创建

- [x] 1.1 重构 `docker-compose.yml` 为基线配置（仅定义服务骨架和环境变量引用）
- [x] 1.2 创建 `docker-compose.local.yml` 本地开发 overlay（端口映射、extra_hosts）
- [x] 1.3 创建 `docker-compose.test.yml` 测试环境 overlay（项目名、镜像、端口 18000）
- [x] 1.4 创建 `docker-compose.prod.yml` 生产环境 overlay（项目名、镜像、端口 8000）

## 2. 环境变量文件创建

- [x] 2.1 创建 `env/.env.local` 本地开发环境变量（Redis 本地、服务地址 localhost）
- [x] 2.2 填充 `env/.env.test` 测试环境变量（ACR 测试仓库、Redis 单节点、服务发现）
- [x] 2.3 创建 `env/.env.prod` 生产环境变量（ACR 生产仓库、Redis Cluster、服务发现）
- [x] 2.4 更新 `.env.example` 环境变量模板（添加所有变量说明）

## 3. 部署指南文档创建

- [x] 3.1 创建 `docs/deploy-guide.md` 文档框架（章节结构）
- [x] 3.2 编写"概述"章节（项目简介、部署架构图）
- [x] 3.3 编写"目录结构说明"章节
- [x] 3.4 编写"环境准备"章节（Docker 安装、网络创建、ACR 登录）
- [x] 3.5 编写"本地开发环境部署"章节（从零开始步骤、启动命令）
- [x] 3.6 编写"测试环境部署"章节（镜像拉取、环境变量、启动命令）
- [x] 3.7 编写"生产环境部署"章节（安全性、回滚策略）
- [x] 3.8 编写"环境变量配置说明"章节（完整变量清单表格）
- [x] 3.9 编写"常见问题解答"章节（启动失败、镜像拉取、健康检查）

## 4. 配置验证

- [x] 4.1 本地开发环境验证（启动服务、健康检查通过）
- [x] 4.2 测试环境配置验证（docker compose config 输出正确）
- [x] 4.3 生产环境配置验证（docker compose config 输出正确）

## 5. Git 配置更新

- [x] 5.1 更新 `.gitignore` 排除敏感环境变量文件（env/.env.local、env/.env.test、env/.env.prod）