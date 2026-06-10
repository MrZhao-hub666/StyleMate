"""边端数据上传接口 — 接收边端 YOLO 分析后的结构化数据"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.db import get_db
from app.models.clothing import Clothing
from app.services.style_profiler import rebuild_style_profile

router = APIRouter(prefix="/api/edge", tags=["edge"])


class ClothingUpload(BaseModel):
    """边端上传的衣物数据结构"""
    zone: str
    category: str
    subcategory: str = "pending_cloud"
    primary_color_hex: str
    primary_color_name: str
    primary_color_ratio: float
    secondary_color_hex: str | None = None
    secondary_color_name: str | None = None
    secondary_color_ratio: float = 0.0
    pattern: str = "未知"
    pattern_confidence: float = 0.0
    neckline: str = "pending_cloud"
    sleeve: str = "pending_cloud"
    fit: str = "pending_cloud"
    length_category: str = "未知"
    fabric: str = "未知"
    fabric_confidence: float = 0.0
    crop_base64: str | None = None
    has_person: bool = False
    needs_cloud: bool = True
    bbox: list | None = None


class BatchUploadRequest(BaseModel):
    clothing_items: list[ClothingUpload]


def _upload_to_clothing(data: ClothingUpload) -> Clothing:
    """将上传数据转为 DB 模型"""
    return Clothing(
        zone=data.zone,
        category=data.category,
        subcategory=data.subcategory,
        primary_color_hex=data.primary_color_hex,
        primary_color_name=data.primary_color_name,
        primary_color_ratio=data.primary_color_ratio,
        secondary_color_hex=data.secondary_color_hex,
        secondary_color_name=data.secondary_color_name,
        secondary_color_ratio=data.secondary_color_ratio,
        pattern=data.pattern,
        pattern_confidence=data.pattern_confidence,
        neckline=data.neckline,
        sleeve=data.sleeve,
        fit=data.fit,
        length_category=data.length_category,
        fabric=data.fabric,
        fabric_confidence=data.fabric_confidence,
        crop_base64=data.crop_base64,
        has_person=data.has_person,
        needs_cloud=data.needs_cloud,
        extra={"bbox": data.bbox} if data.bbox else None,
    )


@router.post("/upload")
async def upload_clothing(data: ClothingUpload, db: AsyncSession = Depends(get_db)):
    """上传单件衣物"""
    clothing = _upload_to_clothing(data)
    db.add(clothing)
    await db.commit()
    await db.refresh(clothing)
    return {"id": clothing.id, "message": "上传成功", "needs_cloud": clothing.needs_cloud}


@router.post("/upload/batch")
async def upload_batch(req: BatchUploadRequest, db: AsyncSession = Depends(get_db)):
    """批量上传衣物"""
    items = [_upload_to_clothing(item) for item in req.clothing_items]
    db.add_all(items)
    await db.commit()
    return {
        "success": len(items),
        "failed": 0,
        "ids": [item.id for item in items],
    }


class QuickUpload(BaseModel):
    """前端拍照/上传快速入库（边端未分析时使用）"""
    crop_base64: str
    zone: str = "single_garment"


@router.post("/upload/quick")
async def quick_upload(data: QuickUpload, db: AsyncSession = Depends(get_db)):
    """前端拍照快速入库（待边端 YOLO 分析补充属性）"""
    clothing = Clothing(
        zone=data.zone,
        crop_base64=data.crop_base64,
        category="衣物",
        needs_cloud=True,
    )
    db.add(clothing)
    await db.commit()
    await db.refresh(clothing)
    return {"id": clothing.id, "message": "已入库，待边端分析补充属性"}


class AttributeUpdate(BaseModel):
    """边端分析完成后回传的属性"""
    category: str = "衣物"
    primary_color_hex: str = "#808080"
    primary_color_name: str = "未知"
    primary_color_ratio: float = 0.0
    secondary_color_hex: str | None = None
    secondary_color_name: str | None = None
    secondary_color_ratio: float = 0.0
    pattern: str = "未知"
    pattern_confidence: float = 0.0
    fabric: str = "未知"
    fabric_confidence: float = 0.0
    length_category: str = "未知"
    has_person: bool = False


@router.put("/upload/{clothing_id}")
async def update_attributes(
    clothing_id: str,
    attrs: AttributeUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """边端分析完成后更新衣物属性 + 触发云端视觉LLM推断细分类"""
    stmt = select(Clothing).where(Clothing.id == clothing_id)
    r = await db.execute(stmt)
    item = r.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "衣物不存在")

    item.category = attrs.category
    item.primary_color_hex = attrs.primary_color_hex
    item.primary_color_name = attrs.primary_color_name
    item.primary_color_ratio = attrs.primary_color_ratio
    item.secondary_color_hex = attrs.secondary_color_hex
    item.secondary_color_name = attrs.secondary_color_name
    item.secondary_color_ratio = attrs.secondary_color_ratio
    item.pattern = attrs.pattern
    item.pattern_confidence = attrs.pattern_confidence
    item.fabric = attrs.fabric
    item.fabric_confidence = attrs.fabric_confidence
    item.length_category = attrs.length_category
    item.has_person = attrs.has_person

    await db.commit()
    await rebuild_style_profile(db)
    await db.commit()

    # 后台异步触发 qwen3.7-plus 看图精细识别
    edge_data = {
        "zone": item.zone,
        "category": item.category,
        "primary_color_name": item.primary_color_name,
        "primary_color_hex": item.primary_color_hex,
        "pattern": item.pattern,
        "fabric": item.fabric,
        "length_category": item.length_category,
        "crop_base64": item.crop_base64,
    }
    background_tasks.add_task(_run_cloud_vision, clothing_id, edge_data)

    return {"id": clothing_id, "message": "属性已更新", "cloud_vision": "pending"}


async def _run_cloud_vision(clothing_id: str, edge_data: dict):
    """后台任务：qwen3.7-plus 看图精细识别全部属性"""
    from app.db import async_session
    from app.services.cloud_vision import infer_clothing_details

    crop_b64 = edge_data.pop("crop_base64", "")
    try:
        result = await infer_clothing_details(edge_data, crop_b64)
    except Exception as e:
        print(f"[cloud_vision] ❌ 推断失败: {e}", flush=True)
        return

    async with async_session() as db:
        stmt = select(Clothing).where(Clothing.id == clothing_id)
        r = await db.execute(stmt)
        item = r.scalar_one_or_none()
        if not item:
            return

        item.subcategory = result.get("subcategory", item.subcategory)
        item.neckline = result.get("neckline", item.neckline)
        item.sleeve = result.get("sleeve", item.sleeve)
        item.fit = result.get("fit", item.fit)
        # Qwen校验后的颜色/图案/面料/长度（覆盖YOLO）
        if result.get("primary_color_name"):
            item.primary_color_name = result["primary_color_name"]
        if result.get("primary_color_hex"):
            item.primary_color_hex = result["primary_color_hex"]
        if result.get("secondary_color_name") is not None:
            item.secondary_color_name = result["secondary_color_name"]
        if result.get("secondary_color_hex") is not None:
            item.secondary_color_hex = result["secondary_color_hex"]
        if result.get("pattern"):
            item.pattern = result["pattern"]
        if result.get("fabric"):
            item.fabric = result["fabric"]
        if result.get("length_category"):
            item.length_category = result["length_category"]
        item.needs_cloud = False
        await db.commit()
