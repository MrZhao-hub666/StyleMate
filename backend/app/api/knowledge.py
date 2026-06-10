"""知识库检索接口"""

from fastapi import APIRouter, Query
from app.knowledge.loader import get_knowledge_base

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/search")
async def search_knowledge(q: str = Query(..., description="搜索关键词"), k: int = 5):
    """RAG 知识检索"""
    kb = get_knowledge_base()
    results = kb.search(q, k=k)
    return {"query": q, "results": results}


@router.post("/rebuild")
async def rebuild_knowledge():
    """强制重建知识库索引"""
    kb = get_knowledge_base()
    kb.build(force=True)
    return {"message": "知识库已重建"}
