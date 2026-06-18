"""穿搭评价接口 — 前端调边端 + 后端调 Qwen 多模态评价"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.agent.reviewer_agent import review_outfit
from app.services.style_profiler import get_style_prompt

router = APIRouter(prefix="/api/review", tags=["review"])


class ReviewRequest(BaseModel):
    outfit_items: list[dict]
    occasion: str = "日常休闲"
    context: str = ""
    edge_attributes: dict | None = None  # 前端调边端后传入


@router.post("")
async def review(req: ReviewRequest, db: AsyncSession = Depends(get_db)):
    image_base64 = ""
    if req.outfit_items and req.outfit_items[0].get("crop_base64"):
        image_base64 = req.outfit_items[0]["crop_base64"]

    style_prompt = await get_style_prompt(db)

    result = await review_outfit(
        image_base64=image_base64,
        edge_attributes=req.edge_attributes or {},
        occasion=req.occasion,
        style_profile=style_prompt,
    )
    return result
