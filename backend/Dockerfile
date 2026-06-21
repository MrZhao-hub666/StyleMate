FROM python:3.13-slim

WORKDIR /app

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# PyPI 镜像源（阿里云优先，官方 PyPI 兜底）
ENV UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ENV UV_EXTRA_INDEX_URL=https://pypi.org/simple/
# 增加超时，应对慢网络（默认30s对大包太短）
ENV UV_HTTP_TIMEOUT=300

# 1. 创建虚拟环境
RUN uv venv

# 2. 先安装 CPU 版 PyTorch（避免 uv 解析到 CUDA 版，省去 ~3.5GB 无用下载）
RUN uv pip install --index-url https://download.pytorch.org/whl/cpu torch

# 3. 复制 pyproject.toml（不复制 uv.lock，避免锁死的旧镜像 URL 覆盖环境变量）
COPY pyproject.toml ./

# 4. 安装依赖（无锁文件 → 从环境变量指定的镜像源实时解析）
RUN uv sync --no-dev

# 5. 复制源码
COPY app/ ./app/

# 6. 创建上传目录
RUN mkdir -p uploads

EXPOSE 9000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]
