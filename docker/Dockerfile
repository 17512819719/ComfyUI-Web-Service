# ComfyUI Web Service Docker 镜像
FROM python:3.11-slim

# 设置维护者信息
LABEL maintainer="ComfyUI Web Service Team"
LABEL description="ComfyUI Web Service - 多模态内容生成工作流管理系统"

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app/backend
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    wget \
    git \
    netcat-openbsd \
    procps \
    vim \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements.txt 并安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY database/ ./database/
COPY scripts/ ./scripts/
COPY docker/start.sh /start.sh
COPY docker/wait-for-it.sh /wait-for-it.sh

# 创建必要的目录
RUN mkdir -p /app/backend/outputs \
    && mkdir -p /app/backend/uploads \
    && mkdir -p /app/logs \
    && mkdir -p /app/temp

# 设置脚本权限
RUN chmod +x /start.sh /wait-for-it.sh

# 创建非root用户
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && chown -R appuser:appuser /app \
    && chown -R appuser:appuser /logs

# 切换到非root用户
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000 8001 8002

# 启动命令
CMD ["/start.sh"]
