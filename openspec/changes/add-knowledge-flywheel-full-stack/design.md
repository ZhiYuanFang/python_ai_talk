## Context

当前项目的母婴知识库 `mother_baby_knowledge` 是随代码发布的静态资源（`data/knowledge/*.md`），服务启动时自动构建到 ChromaDB 向量库。存在以下问题：

1. **知识更新必须发版**：无法通过外部上传动态扩展知识库
2. **用户反馈闭环缺失**：诊疗回答和小贴士都没有用户反馈入口，无法实现数据飞轮
3. **小贴士链路断裂**：Go 侧缺少 TipStream 客户端，无法调用 Python `/v1/tip/stream`
4. **知识质量无法优化**：没有质量评分机制，无法根据用户反馈优化知识权重

本设计旨在构建完整的知识飞轮体系，包括外部知识上传、用户反馈收集、质量评分和治理。

## Goals / Non-Goals

**Goals:**

- 支持外部上传 MD 文件动态扩展知识库
- 诊疗回答返回 answerId，支持用户反馈
- 小贴士反馈接口完整闭环
- 实现知识质量评分和定期清理机制
- 创建 Vue 前端管理页面（独立目录隔离）
- 补全 Go 侧 TipStream 客户端
- 知识数据飞轮：用户反馈间接优化知识质量（👍提升/👎降低质量分）

**Non-Goals:**

- 用户直接提交新知识条目（仅管理员上传）
- 知识版本控制和审核流程（后续迭代）
- 复杂的权限管理系统（简单的 token 验证）
- 大规模分布式部署优化

## Decisions

### 决策 1：诊疗 answerId 设计

**方案 A**：诊疗会话落 MySQL，自增 ID 作为 answerId

**理由**：
- 当前诊疗会话仅存储在 Redis（12h TTL），无法持久化
- 需要持久化会话以便关联用户反馈
- 自增 ID 简单可靠，前端可以直接使用

**数据模型**：

```sql
CREATE TABLE clinic_session (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    wx_id VARCHAR(64) NOT NULL,
    device_no VARCHAR(64) NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    feedback TINYINT NULL,        -- NULL=未反馈, 1=👍, -1=👎
    feedback_at DATETIME NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_wx_id (wx_id),
    INDEX idx_device_no (device_no)
);
```

**SSE 响应扩展**：

```json
// 新增 done 事件
{"type": "done", "answerId": 12345}
```

### 决策 2：反馈机制设计

**方案 A**：反馈间接优化（👍提升质量分，👎降低质量分）

**理由**：
- 避免用户直接贡献低质量知识
- 通过质量分间接影响知识权重，更可控
- 简化实现，专注于反馈闭环

**质量分公式**：

```
quality_score = base_score + (helpful_count / match_count) * 0.5
```

**反馈处理逻辑**：
- 👍：quality_score += 0.1，helpful_count += 1，match_count += 1
- 👎：quality_score -= 0.2，match_count += 1

**清理规则**：
- source=user 且 quality_score < 0.3 → 自动删除
- source=admin → 永不自动删除
- 每周定时清理任务

### 决策 3：向量库元数据扩展

**扩展字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| source | string | "admin"（管理员上传）或 "user" |
| category | string | 知识分类：喂养知识/健康护理/生长发育 |
| doc_id | string | 原始文档 ID |
| file_name | string | 原始文件名 |
| quality_score | float | 质量分数 (0-1) |
| match_count | int | 被匹配次数 |
| helpful_count | int | 有用反馈次数 |
| created_at | string | 创建时间 |
| updated_at | string | 更新时间 |
| chunk_index | int | 文档内 chunk 索引 |
| total_chunks | int | 文档总 chunk 数 |

### 决策 4：Web 前端技术选型

**方案**：Vue 3 + Vite + Element Plus

**理由**：
- Vue 学习曲线平缓，生态成熟
- Vite 构建速度快，开发体验好
- Element Plus 提供丰富的 UI 组件
- 与 Python 服务端零耦合，独立目录

**目录结构**：

```
web/
├── src/
│   ├── components/
│   │   ├── KnowledgeList.vue
│   │   ├── KnowledgeForm.vue
│   │   ├── StatsCard.vue
│   │   └── FeedbackChart.vue
│   ├── views/
│   │   ├── Dashboard.vue
│   │   ├── KnowledgeManage.vue
│   │   └── FeedbackStats.vue
│   ├── api/
│   │   └── knowledge.js
│   ├── App.vue
│   └── main.js
├── public/
│   └── index.html
├── dist/
├── package.json
├── vite.config.js
└── tailwind.config.js
```

**部署方式**：
- 开发时：`npm run dev`，通过 proxy 调用后端 API
- 部署时：构建产物 `dist/` 随 Docker 镜像打包，FastAPI 静态文件托管

### 决策 5：知识上传存储方案

**方案**：本地文件系统 + ChromaDB

**理由**：
- 简单直接，与现有架构兼容
- 需要挂载 volume 持久化
- 后续可扩展到对象存储

**存储路径**：
- 原始 MD 文件：`data/knowledge/`
- 向量库：`data/chroma_db/`

### 决策 6：反馈接口设计

**Python 侧接口**：

| API | 方法 | 说明 |
|-----|------|------|
| `/v1/tip/feedback` | POST | 接收小贴士反馈 |
| `/v1/clinic/feedback` | POST | 接收诊疗回答反馈 |

**请求体**：

```json
{
    "answerId": 12345,
    "feedback": 1,           // 1=👍, -1=👎
    "type": "clinic"         // "tip" 或 "clinic"
}
```

**Go 侧接口**：

| API | 方法 | 说明 |
|-----|------|------|
| `/tip/feedback` | POST | 接收小贴士反馈（Flutter 调用） |
| `/clinic/feedback` | POST | 接收诊疗反馈（Flutter 调用） |

**数据流转**：
```
Flutter → Go 接口 → Go 落库 → Python 反馈接口 → 更新向量库质量分
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 前端构建产物体积大，影响 Docker 镜像大小 | 使用 Vite 构建优化，启用 gzip 压缩，CDN 托管静态资源 |
| 向量库元数据扩展可能影响现有检索逻辑 | 向后兼容，旧数据使用默认值，新增字段仅在反馈处理时使用 |
| 用户反馈可能被恶意刷票 | 添加频率限制（同一用户 5 分钟内最多反馈 3 次） |
| 诊疗会话落库增加数据库写入压力 | 使用批量写入或异步写入，设置合理索引 |
| 小贴士链路补全需要修改 Go 代码 | Go 代码不在当前工作目录，需要手动同步修改 |
| 知识清理可能误删有用知识 | 设置合理阈值（0.3），仅清理 source=user 的知识 |

## Migration Plan

### 部署步骤

1. **Python 服务**：部署新代码，启动时自动检测并初始化扩展字段
2. **Go 服务**：部署新代码，执行数据库迁移（创建 clinic_session、tip_feedback、clinic_feedback 表）
3. **Flutter 客户端**：部署新版本，诊疗页面新增反馈按钮
4. **Web 前端**：构建并部署到 Python 服务静态目录

### 回滚策略

1. **Python 服务**：回滚到上一版本，向量库元数据向后兼容
2. **Go 服务**：回滚到上一版本，保留数据库表（仅不再写入）
3. **Flutter 客户端**：回滚到上一版本，反馈按钮被移除

## Open Questions

1. Go 侧诊疗会话表放在哪个数据库？（ai_voice_history 还是 ai_voice_voice）
2. Flutter 侧诊疗反馈的 state management 如何实现？（复用 tips 的 provider 模式还是新建）
3. Web 前端是否需要认证？（简单 token 还是完整登录）
4. 知识分类是否需要支持自定义？（还是固定三类：喂养知识/健康护理/生长发育）
