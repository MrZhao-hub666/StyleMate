FROM python:3.13-slim

WORKDIR /app

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# PyPI 镜像源（阿里云优先，官方 PyPI 兜底）
ENV UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ENV UV_EXTRA_INDEX_URL=https://pypi.org/simple/

# 复制依赖（不用 --frozen，因为 lockfile 可能锁着无法访问的镜像源 URL）
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev

# 复制源码
COPY app/ ./app/

# 创建上传目录
RUN mkdir -p uploads

EXPOSE 9000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]
