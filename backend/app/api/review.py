"""穿搭评价接口 — 边端YOLO分析 + qwen3.7-plus 多模态评价"""

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.agent.reviewer_agent import review_outfit
from app.services.style_profiler import get_style_prompt

router = APIRouter(prefix="/api/review", tags=["review"])

PFX = "[review]"
EDGE_URL = "http://localhost:9001/analyze"


class ReviewRequest(BaseModel):
    outfit_items: list[dict]
    occasion: str = "日常休闲"
    context: str = ""


async def _call_edge_analysis(image_base64: str) -> dict:
    """调用边端 YOLO 分析衣物属性"""
    try:
        b64 = image_base64.split(",")[-1] if "," in image_base64 else image_base64
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                EDGE_URL,
                json={"image_base64": b64, "zone": "outfit"},
            )
            resp.raise_for_status()
            data = resp.json()
            print(f"{PFX} 边端分析完成: 品类={data.get('category')} 颜色={data.get('primary_color_name')} 图案={data.get('pattern')}", flush=True)
            return data
    except Exception as e:
        print(f"{PFX} 边端分析失败（将仅用图评价）: {e}", flush=True)
        return {}


@router.post("")
async def review(req: ReviewRequest, db: AsyncSession = Depends(get_db)):
    """
    穿搭评价：
    1. 边端 YOLO 提取衣物属性（仅供参考）
    2. qwen3.7-plus 看图评价
    """
    image_base64 = ""
    if req.outfit_items and req.outfit_items[0].get("crop_base64"):
        image_base64 = req.outfit_items[0]["crop_base64"]

    # 边端 YOLO 分析 + 风格画像（并行）
    style_prompt = await get_style_prompt(db)
    edge_attrs = {}
    if image_base64:
        edge_attrs = await _call_edge_analysis(image_base64)

    result = await review_outfit(
        image_base64=image_base64,
        edge_attributes=edge_attrs,
        occasion=req.occasion,
        style_profile=style_prompt,
    )
    return result
