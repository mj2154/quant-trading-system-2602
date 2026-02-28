FROM python:3.14-slim

# 从官方镜像复制 uv 二进制
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
ENV PATH=/bin:$PATH

WORKDIR /app

# 复制项目文件
COPY pyproject.toml ./
COPY src/ ./src/
COPY .env ./
COPY keys/ ./keys/

# 安装依赖
RUN uv sync

# 启动应用
CMD ["uv", "run", "python", "src/main.py"]
