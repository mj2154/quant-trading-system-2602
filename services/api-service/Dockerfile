# API 服务 Dockerfile - 简化配置
FROM python:3.14-slim

# 从官方镜像复制 uv 二进制
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
ENV PATH=/bin:$PATH

WORKDIR /app

# 复制项目文件
COPY pyproject.toml ./
COPY src/ ./src/

# 安装依赖
RUN uv sync

# 暴露端口
EXPOSE 8000

# 启动应用
# CMD ["uv", "run", "python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
