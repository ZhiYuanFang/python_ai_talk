FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./

RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --without dev

# 预下载 BGE-small-zh-v1.5 Embedding 模型到 data/models 目录
# 避免容器启动时从 HuggingFace 下载（国内网络不稳定）
# 模型约 90MB，打包进镜像后容器启动更快且不依赖运行时网络
RUN mkdir -p data/models && \
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-zh-v1.5', cache_folder='data/models')"

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 复制 Python 依赖（site-packages 和可执行文件）
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制项目代码（包含 app 源码、data/knowledge 知识文档等）
COPY . .

# 从 builder 阶段复制预下载的模型（放在 COPY . . 之后，避免被本地空目录覆盖）
COPY --from=builder /app/data/models /app/data/models

# 确保向量数据库目录存在（运行时持久化用，建议挂载 volume）
RUN mkdir -p data/chroma_db

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --retries=6 \
    CMD wget -q -O - http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
