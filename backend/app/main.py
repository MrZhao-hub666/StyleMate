"""
StyleMate 云端后端 — FastAPI 入口
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import HOST, PORT, UPLOAD_DIR
from app.db import init_db
from app.middleware.error_handler import TraceMiddleware
from app.api import edge, wardrobe, recommend, review, portrait, knowledge, profile
from app.services.cleanup import cleanup_generated


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时创建数据库表 + 清理过期生成文件"""
    await init_db()
    cleanup_generated()
    yield


app = FastAPI(
    title="StyleMate API",
    description="边云协同智能穿搭助手 — 云端服务",
    version="0.1.0",
    lifespan=lifespan,
)

# === 中间件：先注册内部中间件，再 CORS ===
app.add_middleware(TraceMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === 路由 ===
app.include_router(edge.router)
app.include_router(wardrobe.router)
app.include_router(recommend.router)
app.include_router(review.router)
app.include_router(portrait.router)
app.include_router(knowledge.router)
app.include_router(profile.router)

# === 静态文件 ===
UPLOAD_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.get("/api/health")
async def health():
    """健康检查"""
    return {"status": "ok", "service": "StyleMate Backend"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
