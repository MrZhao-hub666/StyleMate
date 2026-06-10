"""用户个人资料接口"""

import uuid
import os
import asyncio
from pathlib import Path
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.db import get_db
from app.models.user import UserProfile, GalleryImage, GalleryImageAnalysis
from app.services.style_profiler import rebuild_style_profile
from app.config import UPLOAD_DIR

router = APIRouter(prefix="/api/profile", tags=["profile"])

AVATAR_DIR = UPLOAD_DIR / "avatars"
AVATAR_DIR.mkdir(exist_ok=True)
GALLERY_DIR = UPLOAD_DIR / "gallery"
GALLERY_DIR.mkdir(exist_ok=True)


class ProfileUpdate(BaseModel):
    nickname: str | None = None
    gender: str | None = None
    birthdate: str | None = None   # YYYY-MM-DD
    height: float | None = None
    weight: float | None = None
    city: str | None = None


async def _get_or_create_profile(db: AsyncSession) -> UserProfile:
    stmt = select(UserProfile).limit(1)
    r = await db.execute(stmt)
    profile = r.scalar_one_or_none()
    if not profile:
        profile = UserProfile()
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


def _calc_age(birthdate: date | None) -> int | None:
    if not birthdate:
        return None
    today = date.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))


def _calc_zodiac(birthdate: date | None) -> str:
    """根据公历日期计算星座"""
    if not birthdate:
        return "未知"
    m, d = birthdate.month, birthdate.day
    # (起始月, 起始日, 结束月, 结束日, 星座名)
    signs = [
        (1,  20, 2, 18, "水瓶座"),
        (2,  19, 3, 20, "双鱼座"),
        (3,  21, 4, 19, "白羊座"),
        (4,  20, 5, 20, "金牛座"),
        (5,  21, 6, 21, "双子座"),
        (6,  22, 7, 22, "巨蟹座"),
        (7,  23, 8, 22, "狮子座"),
        (8,  23, 9, 22, "处女座"),
        (9,  23, 10, 23, "天秤座"),
        (10, 24, 11, 22, "天蝎座"),
        (11, 23, 12, 21, "射手座"),
        (12, 22, 1, 19, "摩羯座"),
    ]
    for sm, sd, em, ed, name in signs:
        if (m == sm and d >= sd) or (m == em and d <= ed):
            return name
    return "摩羯座"  # 12月22日-1月19日跨年边界


def _to_profile_dict(p: UserProfile) -> dict:
    return {
        "id": p.id,
        "nickname": p.nickname,
        "avatar_path": p.avatar_path,
        "gender": p.gender,
        "birthdate": str(p.birthdate) if p.birthdate else None,
        "age": _calc_age(p.birthdate),
        "zodiac": _calc_zodiac(p.birthdate),
        "height": p.height,
        "weight": p.weight,
        "city": p.city,
    }


@router.get("")
async def get_profile(db: AsyncSession = Depends(get_db)):
    p = await _get_or_create_profile(db)
    return _to_profile_dict(p)


@router.put("")
async def update_profile(data: ProfileUpdate, db: AsyncSession = Depends(get_db)):
    p = await _get_or_create_profile(db)
    if data.nickname is not None:
        p.nickname = data.nickname
    if data.gender is not None:
        p.gender = data.gender
    if data.birthdate is not None:
        try:
            p.birthdate = date.fromisoformat(data.birthdate)
        except ValueError:
            raise HTTPException(400, "日期格式错误，应为 YYYY-MM-DD")
    if data.height is not None:
        p.height = data.height
    if data.weight is not None:
        p.weight = data.weight
    if data.city is not None:
        p.city = data.city
    await db.commit()
    await db.refresh(p)
    return _to_profile_dict(p)


@router.post("/avatar")
async def upload_avatar(file: UploadFile, db: AsyncSession = Depends(get_db)):
    p = await _get_or_create_profile(db)
    ext = Path(file.filename).suffix or ".jpg"
    filename = f"avatar_{uuid.uuid4().hex[:8]}{ext}"
    filepath = AVATAR_DIR / filename
    content = await file.read()
    filepath.write_bytes(content)
    p.avatar_path = f"/uploads/avatars/{filename}"
    await db.commit()
    return {"avatar_path": p.avatar_path}


# === 个人相册 ===

@router.get("/gallery")
async def list_gallery(db: AsyncSession = Depends(get_db)):
    stmt = select(GalleryImage).order_by(GalleryImage.created_at.desc())
    r = await db.execute(stmt)
    images = r.scalars().all()

    # 批量查询分析状态
    img_ids = [i.id for i in images]
    analyzed_map = {}
    if img_ids:
        stmt2 = select(GalleryImageAnalysis).where(
            GalleryImageAnalysis.gallery_image_id.in_(img_ids)
        )
        r2 = await db.execute(stmt2)
        for a in r2.scalars().all():
            analyzed_map[a.gallery_image_id] = a.analyzed

    return [
        {
            "id": i.id, "filename": i.filename, "filepath": i.filepath,
            "tag": i.tag, "width": i.width, "height": i.height,
            "analyzed": analyzed_map.get(i.id, False),
            "created_at": str(i.created_at),
        }
        for i in images
    ]


async def _run_gallery_analysis(img_id: str, full_path: Path):
    """后台执行相册照片分析（创建独立 DB session，不受请求生命周期影响）"""
    from app.db import async_session
    from app.services.style_profiler import analyze_gallery_photo

    PFX = "[gallery_analysis]"
    print(f"{PFX} ========== 开始分析 img={img_id[:8]}... path={full_path.name} ==========", flush=True)

    # 1) 调用边端 HTTP 分析
    try:
        result = await asyncio.to_thread(analyze_gallery_photo, str(full_path))
        print(f"{PFX} 边端返回: has_person={result.get('has_person')} face={bool(result.get('face_crop_b64'))} colors={len(result.get('colors', []))}", flush=True)
    except Exception as e:
        result = {"has_person": False, "error": str(e)}
        print(f"{PFX} 边端调用异常: {e}", flush=True)

    # 2) 用自己的 session 写入 DB
    async with async_session() as db:
        try:
            analysis = GalleryImageAnalysis(
                gallery_image_id=img_id,
                has_person=result.get("has_person", False),
                person_count=result.get("person_count", 0),
                clothing_colors=result.get("colors", []),
                clothing_categories=result.get("categories", []),
                dominant_pattern=result.get("dominant_pattern", "未知"),
                face_crop_base64=result.get("face_crop_b64"),
                analyzed=True,
                analyze_error=result.get("error"),
                analyzed_at=datetime.now(),
            )
            db.add(analysis)

            await rebuild_style_profile(db)
            await db.commit()
            print(f"{PFX} ✅ 分析完成: img={img_id[:8]}... 有人={result.get('has_person')} 人脸={bool(result.get('face_crop_b64'))}", flush=True)
        except Exception as e:
            print(f"{PFX} ❌ 写入DB失败: {e}", flush=True)
            try:
                analysis = GalleryImageAnalysis(
                    gallery_image_id=img_id,
                    analyzed=False,
                    analyze_error=str(e),
                    analyzed_at=datetime.now(),
                )
                db.add(analysis)
                await db.commit()
            except Exception:
                pass


@router.post("/gallery/upload")
async def upload_gallery(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    tag: str = "portrait",
    db: AsyncSession = Depends(get_db),
):
    ext = Path(file.filename).suffix or ".jpg"
    filename = f"{uuid.uuid4().hex[:8]}{ext}"
    filepath = GALLERY_DIR / filename
    content = await file.read()
    filepath.write_bytes(content)
    img = GalleryImage(
        filename=file.filename,
        filepath=f"/uploads/gallery/{filename}",
        tag=tag,
    )
    db.add(img)
    await db.commit()
    await db.refresh(img)

    # 后台异步分析（不阻塞上传响应）
    full_path = GALLERY_DIR / filename
    background_tasks.add_task(_run_gallery_analysis, img.id, full_path)

    return {"id": img.id, "filepath": img.filepath, "tag": img.tag}


@router.delete("/gallery/{image_id}")
async def delete_gallery(image_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(GalleryImage).where(GalleryImage.id == image_id)
    r = await db.execute(stmt)
    img = r.scalar_one_or_none()
    if not img:
        raise HTTPException(404, "图片不存在")

    # 删除物理文件
    rel = img.filepath
    if rel.startswith("/uploads/"):
        rel = rel[len("/uploads/"):]
    full_path = UPLOAD_DIR / rel
    if full_path.exists():
        os.remove(full_path)

    # 删除关联分析记录
    stmt2 = delete(GalleryImageAnalysis).where(GalleryImageAnalysis.gallery_image_id == image_id)
    await db.execute(stmt2)

    # 删除图片记录
    await db.delete(img)
    await db.commit()

    # 重建风格画像
    await rebuild_style_profile(db)
    await db.commit()

    return {"message": "已删除"}


# === 风格画像 ===

@router.get("/style")
async def get_style_profile(db: AsyncSession = Depends(get_db)):
    """获取用户风格画像"""
    stmt = select(UserStyleProfile).limit(1)
    r = await db.execute(stmt)
    profile = r.scalar_one_or_none()

    if not profile:
        # 首次访问：尝试构建
        await rebuild_style_profile(db)
        await db.commit()
        r2 = await db.execute(stmt)
        profile = r2.scalar_one_or_none()

    if not profile:
        return {"message": "暂无风格数据，请上传相册照片和衣橱物品"}

    return {
        "color_preferences": profile.color_preferences,
        "pattern_preferences": profile.pattern_preferences,
        "category_preferences": profile.category_preferences,
        "style_tendency": profile.style_tendency,
        "dominant_colors_hex": profile.dominant_colors_hex,
        "gallery_photo_count": profile.gallery_photo_count,
        "wardrobe_item_count": profile.wardrobe_item_count,
        "confidence": profile.confidence,
        "updated_at": str(profile.updated_at) if profile.updated_at else None,
    }


@router.post("/style/rebuild")
async def manual_rebuild_style(db: AsyncSession = Depends(get_db)):
    """手动触发风格画像重建"""
    profile = await rebuild_style_profile(db)
    await db.commit()
    return {
        "message": "风格画像已更新",
        "style_tendency": profile.style_tendency if profile else None,
    }
