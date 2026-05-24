FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
ENV PATH=/bin:$PATH

WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/
COPY main.py ./

RUN uv sync

CMD ["uv", "run", "python", "main.py"]
