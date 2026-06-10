"""穿搭推荐接口 — 文字方案 + 3张预览图（万相2.7-pro）"""

import uuid
import asyncio
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db
from app.agent.stylist_agent import recommend_outfit
from app.models.clothing import Clothing
from app.models.user import GalleryImage, GalleryImageAnalysis
from app.services.style_profiler import get_style_prompt
from app.services.image_gen import image_to_image
from app.config import UPLOAD_DIR, DASHSCOPE_IMAGE_MODEL_PRO

router = APIRouter(prefix="/api/recommend", tags=["recommend"])
GENERATED_DIR = UPLOAD_DIR / "generated"
GENERATED_DIR.mkdir(exist_ok=True)
PFX = "[recommend]"


class RecommendRequest(BaseModel):
    occasion: str
    preference: str = ""
    city: str = "北京"
    photo_data: str | None = None
    force_text_only: bool = False


def _expand_items(plans: list[dict], wardrobe: list[dict]) -> list[dict]:
    """将 DeepSeek 返回的 UUID 字符串展开为可读文字"""
    by_id = {w["id"]: w for w in wardrobe if w.get("id")}
    for plan in plans:
        expanded = []
        for item in plan.get("items", []):
            if isinstance(item, str) and item in by_id:
                w = by_id[item]
                expanded.append(f"{w['primary_color_name']} {w['category']}")
            elif isinstance(item, dict):
                expanded.append(item.get("primary_color_name", "") or item.get("id", ""))
            else:
                expanded.append(str(item))
        plan["items"] = expanded
    return plans


def _build_clothing_prompt(plan: dict, wardrobe: list[dict]) -> str:
    """从推荐方案的原始UUID项构建生图 prompt"""
    by_id = {w["id"]: w for w in wardrobe if w.get("id")}
    lines = []
    for item in plan.get("_raw_items", plan.get("items", [])):
        item_id = item if isinstance(item, str) else item.get("id", "")
        if item_id in by_id:
            w = by_id[item_id]
            desc = f"{w.get('primary_color_name','')}色 {w.get('pattern','')} {w.get('fabric','')} {w.get('category','')}"
            lines.append(f"- {desc.strip().replace('  ',' ')}")
    items_text = "\n".join(lines) if lines else plan.get("name", "整套搭配")
    return (
        f"请基于这张人物照片生成穿搭预览。\n"
        f"必须完全保留人物面部五官、发型、肤色不变。\n"
        f"将服装更换为以下搭配：\n{items_text}\n"
        f"场景：{plan.get('name','')}的得体背景。\n"
        f"画质高清，光线自然柔和。"
    )


async def _get_face_photo(photo_data: str | None, db: AsyncSession) -> str | None:
    if photo_data:
        return photo_data.split(",")[-1] if "," in photo_data else photo_data
    stmt = (
        select(GalleryImage, GalleryImageAnalysis)
        .join(GalleryImageAnalysis, GalleryImageAnalysis.gallery_image_id == GalleryImage.id)
        .where(GalleryImageAnalysis.has_person == True)
        .order_by(GalleryImage.created_at.desc())
        .limit(1)
    )
    r = await db.execute(stmt)
    row = r.first()
    if not row:
        return None
    img_obj, _ = row
    rel = img_obj.filepath
    if rel.startswith("/uploads/"):
        rel = rel[len("/uploads/"):]
    disk_path = UPLOAD_DIR / rel
    if not disk_path.exists():
        return None
    import base64
    return base64.b64encode(disk_path.read_bytes()).decode()


async def _gen_one_preview(face_b64: str, plan: dict, wardrobe: list[dict]) -> str | None:
    """生成单张预览图，返回URL或None"""
    prompt = _build_clothing_prompt(plan, wardrobe)
    img_result = await image_to_image(face_b64, prompt, model=DASHSCOPE_IMAGE_MODEL_PRO)
    if "error" in img_result or not img_result.get("images"):
        return None
    import base64
    b64_img = img_result["images"][0]
    filename = f"recommend_{uuid.uuid4().hex[:8]}.jpg"
    filepath = GENERATED_DIR / filename
    try:
        filepath.write_bytes(base64.b64decode(b64_img))
        return f"/uploads/generated/{filename}"
    except Exception:
        return None


@router.post("")
async def recommend(req: RecommendRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(Clothing).order_by(Clothing.created_at.desc())
    r = await db.execute(stmt)
    items = r.scalars().all()
    wardrobe = [
        {
            "id": i.id, "zone": i.zone, "category": i.category,
            "primary_color_name": i.primary_color_name, "primary_color_hex": i.primary_color_hex,
            "pattern": i.pattern, "fabric": i.fabric, "length_category": i.length_category,
        }
        for i in items
    ]

    style_prompt = await get_style_prompt(db)
    result = await recommend_outfit(
        occasion=req.occasion, preference=req.preference, city=req.city,
        wardrobe_items=wardrobe, style_profile=style_prompt,
    )
    plans = result.get("recommendations", [])

    # 保存原始 items 供生图用（展开前）
    for p in plans:
        p["_raw_items"] = list(p.get("items", []))

    # 展开 UUID → 可读文字
    plans = _expand_items(plans, wardrobe)
    result["recommendations"] = plans

    # 前置检查
    face_b64 = await _get_face_photo(req.photo_data, db)
    has_face = bool(face_b64)
    has_wardrobe = len(wardrobe) > 0

    if not has_face or not has_wardrobe:
        if req.force_text_only:
            return result
        missing = []
        if not has_face:
            missing.append("请先上传本人照片（或完善个人相册），否则 AI 无法生成试穿效果")
        if not has_wardrobe:
            missing.append("请先在个人衣橱中添加衣物，否则 AI 无法匹配你的穿搭")
        result["preview_warning"] = "；\n".join(missing) + "\n\n是否继续获取纯文字搭配建议？"
        result["need_confirm"] = True
        return result

    # 并行生成 3 张预览图
    print(f"{PFX} 并行生成 {len(plans)} 张预览图...", flush=True)
    tasks = [_gen_one_preview(face_b64, plan, wardrobe) for plan in plans[:3]]
    preview_urls = await asyncio.gather(*tasks, return_exceptions=True)
    for i, p in enumerate(plans):
        url = preview_urls[i] if i < len(preview_urls) and not isinstance(preview_urls[i], Exception) else None
        p["preview_url"] = url
        if url:
            print(f"{PFX} [{i+1}] {p.get('name')} → 预览图 OK", flush=True)
        else:
            print(f"{PFX} [{i+1}] {p.get('name')} → 预览图失败", flush=True)

    return result
