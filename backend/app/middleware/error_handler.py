"""
请求追踪 + 异常处理中间件

提供：
  - 全局异常捕获与 JSON 格式错误响应
  - 请求耗时日志
  - trace_id 生成与追踪
"""

import time
import uuid
import logging
import traceback
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# ====== 日志配置 ======
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("stylemate")


class TraceMiddleware(BaseHTTPMiddleware):
    """请求追踪与异常捕获"""

    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("X-Trace-Id", uuid.uuid4().hex[:12])
        start = time.time()

        # 注入 trace_id 到请求上下文
        request.state.trace_id = trace_id

        try:
            response: Response = await call_next(request)
        except Exception as exc:
            elapsed = (time.time() - start) * 1000
            logger.error(
                f"[{trace_id}] {request.method} {request.url.path} → "
                f"500 ({elapsed:.0f}ms)\n{traceback.format_exc()}"
            )
            return JSONResponse(
                status_code=500,
                content={
                    "detail": str(exc) if str(exc) else "服务器内部错误",
                    "trace_id": trace_id,
                },
            )

        elapsed = (time.time() - start) * 1000
        status = response.status_code

        level = logging.WARNING if status >= 400 else logging.INFO
        logger.log(
            level,
            f"[{trace_id}] {request.method} {request.url.path} → "
            f"{status} ({elapsed:.0f}ms)",
        )

        # 注入 trace_id 到响应头
        response.headers["X-Trace-Id"] = trace_id
        return response
