"""数字衣橱管理接口"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db
from app.models.clothing import Clothing
from app.services.style_profiler import rebuild_style_profile

router = APIRouter(prefix="/api/wardrobe", tags=["wardrobe"])


@router.get("")
async def list_wardrobe(
    zone: str = "",
    category: str = "",
    db: AsyncSession = Depends(get_db),
):
    """获取衣橱列表，支持按 zone/category 筛选"""
    stmt = select(Clothing)
    if zone:
        stmt = stmt.where(Clothing.zone == zone)
    if category:
        stmt = stmt.where(Clothing.category == category)
    stmt = stmt.order_by(Clothing.created_at.desc())
    result = await db.execute(stmt)
    items = result.scalars().all()

    return [
        {
            "id": item.id,
            "zone": item.zone,
            "category": item.category,
            "subcategory": item.subcategory,
            "primary_color_hex": item.primary_color_hex,
            "primary_color_name": item.primary_color_name,
            "primary_color_ratio": item.primary_color_ratio,
            "secondary_color_hex": item.secondary_color_hex,
            "secondary_color_name": item.secondary_color_name,
            "pattern": item.pattern,
            "fabric": item.fabric,
            "length_category": item.length_category,
            "neckline": item.neckline,
            "sleeve": item.sleeve,
            "fit": item.fit,
            "needs_cloud": item.needs_cloud,
            "crop_base64": item.crop_base64,
            "created_at": str(item.created_at),
        }
        for item in items
    ]


@router.get("/{clothing_id}")
async def get_clothing(clothing_id: str, db: AsyncSession = Depends(get_db)):
    """获取单件衣物详情（含裁剪图 base64）"""
    stmt = select(Clothing).where(Clothing.id == clothing_id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="衣物不存在")

    return {
        "id": item.id,
        "zone": item.zone,
        "category": item.category,
        "subcategory": item.subcategory,
        "primary_color_hex": item.primary_color_hex,
        "primary_color_name": item.primary_color_name,
        "primary_color_ratio": item.primary_color_ratio,
        "secondary_color_hex": item.secondary_color_hex,
        "secondary_color_name": item.secondary_color_name,
        "secondary_color_ratio": item.secondary_color_ratio,
        "pattern": item.pattern,
        "pattern_confidence": item.pattern_confidence,
        "neckline": item.neckline,
        "sleeve": item.sleeve,
        "fit": item.fit,
        "length_category": item.length_category,
        "fabric": item.fabric,
        "fabric_confidence": item.fabric_confidence,
        "has_person": item.has_person,
        "needs_cloud": item.needs_cloud,
        "crop_base64": item.crop_base64,
        "created_at": str(item.created_at),
    }


@router.delete("/{clothing_id}")
async def delete_clothing(clothing_id: str, db: AsyncSession = Depends(get_db)):
    """删除衣物"""
    stmt = select(Clothing).where(Clothing.id == clothing_id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="衣物不存在")
    await db.delete(item)
    await db.commit()
    # 删除后重建风格画像
    await rebuild_style_profile(db)
    await db.commit()
    return {"message": "已删除"}
