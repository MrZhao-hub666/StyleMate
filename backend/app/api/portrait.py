"""创意生成接口"""

import base64
import shutil
import uuid
import time
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db
from app.agent.portrait_agent import optimize_prompt
from app.models.user import UserProfile, GalleryImageAnalysis, GalleryImage
from app.services.style_profiler import get_style_prompt
from app.services.image_gen import image_to_image
from app.config import UPLOAD_DIR

router = APIRouter(prefix="/api/portrait", tags=["portrait"])

GENERATED_DIR = UPLOAD_DIR / "generated"
GENERATED_DIR.mkdir(exist_ok=True)
GALLERY_DIR = UPLOAD_DIR / "gallery"
GALLERY_DIR.mkdir(exist_ok=True)


PFX = "[portrait]"


class PortraitRequest(BaseModel):
    description: str
    style: str = ""
    face_image: str | None = None  # base64 人脸照片（可选）


class SavePortraitRequest(BaseModel):
    image_url: str  # 如 /uploads/generated/gen_xxx.jpg


async def _pick_best_face(db: AsyncSession) -> str | None:
    """从相册中选取最新一张含人的原图"""
    print(f"{PFX} [1/5 人脸] 查询相册含人照片原图...", flush=True)
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
        print(f"{PFX} [1/5 人脸] ⚠ 相册中无含人照片", flush=True)
        return None

    img_obj, _ = row
    # 从 filepath 解析磁盘路径，如 "/uploads/gallery/xxx.jpg" → UPLOAD_DIR/gallery/xxx.jpg
    rel = img_obj.filepath
    if rel.startswith("/uploads/"):
        rel = rel[len("/uploads/"):]
    disk_path = UPLOAD_DIR / rel

    if not disk_path.exists():
        print(f"{PFX} [1/5 人脸] ⚠ 原图文件不存在: {disk_path}", flush=True)
        return None

    img_bytes = disk_path.read_bytes()
    b64 = base64.b64encode(img_bytes).decode()
    print(f"{PFX} [1/5 人脸] ✅ 读取相册原图: {img_obj.filename} ({len(img_bytes)}bytes, b64长度={len(b64)})", flush=True)
    return b64


@router.post("/generate")
async def generate_portrait(req: PortraitRequest, db: AsyncSession = Depends(get_db)):
    """创意生图：优化 prompt → 调 DashScope 生图 → 返回图片"""
    t0 = time.time()
    print(f"{PFX} ========== 开始生成 ==========", flush=True)
    print(f"{PFX} 描述: {req.description[:80]}... 用户传图: {bool(req.face_image)}", flush=True)

    # 1) 读取用户性别
    print(f"{PFX} [0/5 性别] 读取用户资料...", flush=True)
    gender = "未设置"
    p_stmt = select(UserProfile).limit(1)
    p_r = await db.execute(p_stmt)
    user_profile = p_r.scalar_one_or_none()
    if user_profile and user_profile.gender not in ("未设置", None, ""):
        gender = user_profile.gender
        print(f"{PFX} [0/5 性别] ✅ 性别={gender}", flush=True)
    else:
        print(f"{PFX} [0/5 性别] ⚠ 未设置性别", flush=True)

    # 2) 读取风格画像
    print(f"{PFX} [1/5 风格] 读取用户风格画像...", flush=True)
    style_prompt = await get_style_prompt(db)
    if style_prompt:
        print(f"{PFX} [1/5 风格] ✅ 风格画像已加载 ({len(style_prompt)}字符)", flush=True)
    else:
        print(f"{PFX} [1/5 风格] ⚠ 暂无风格画像", flush=True)

    # 3) 人脸来源
    face_b64 = req.face_image
    if not face_b64:
        print(f"{PFX} [2/5 人脸] 用户未传图，从相册自动选取...", flush=True)
        face_b64 = await _pick_best_face(db)
        if face_b64:
            print(f"{PFX} [2/5 人脸] ✅ 已从相册选取", flush=True)
        else:
            print(f"{PFX} [2/5 人脸] ❌ 相册也无可用照片", flush=True)
            raise HTTPException(400, "请先上传照片或确保个人相册中有含人照片")
    else:
        print(f"{PFX} [2/5 人脸] ✅ 用户已上传照片 (长度={len(face_b64)}字符)", flush=True)

    # 4) 优化 prompt
    print(f"{PFX} [3/5 Prompt] LLM 优化生图提示词 (gender={gender})...", flush=True)
    t2 = time.time()
    prompt = await optimize_prompt(
        user_description=req.description,
        style=req.style,
        style_profile=style_prompt,
        has_face=True,
        gender=gender,
    )
    print(f"{PFX} [3/5 Prompt] ✅ 耗时={(time.time()-t2)*1000:.0f}ms → {prompt[:100]}...", flush=True)

    # 5) 生图
    print(f"{PFX} [4/5 生图] 图生图 性别={gender} 开始调用 DashScope...", flush=True)
    t3 = time.time()
    result = await image_to_image(face_b64, prompt, gender=gender)

    if "error" in result:
        print(f"{PFX} [4/5 生图] ❌ 失败: {result['error']}", flush=True)
        return {
            "original": req.description,
            "optimized_prompt": prompt,
            "images": [],
            "generation_model": result.get("model", "unknown"),
            "error": result["error"],
        }

    print(f"{PFX} [4/5 生图] ✅ 模型={result.get('model')} 耗时={(time.time()-t3)*1000:.0f}ms 生成{len(result.get('images',[]))}张", flush=True)

    # 5) 保存到磁盘
    images = []
    gen_model = result.get("model", "unknown")
    b64_images = result.get("images", [])

    for i, b64 in enumerate(b64_images):
        filename = f"gen_{uuid.uuid4().hex[:12]}.jpg"
        filepath = GENERATED_DIR / filename
        try:
            img_bytes = base64.b64decode(b64)
            filepath.write_bytes(img_bytes)
            images.append(f"/uploads/generated/{filename}")
            print(f"{PFX} [5/5 保存] ✅ [{i+1}/{len(b64_images)}] {filename} ({len(img_bytes)}bytes)", flush=True)
        except Exception as e:
            print(f"{PFX} [5/5 保存] ❌ [{i+1}] 写入失败: {e}", flush=True)

    print(f"{PFX} ========== 完成 总耗时={(time.time()-t0)*1000:.0f}ms ==========", flush=True)
    return {
        "original": req.description,
        "optimized_prompt": prompt,
        "images": images,
        "generation_model": gen_model,
    }


@router.post("/save")
async def save_portrait(
    req: SavePortraitRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """将生成的写真保存到创意写真相册"""
    # 解析文件路径
    url = req.image_url
    if url.startswith("/uploads/"):
        rel = url[len("/uploads/"):]
    else:
        rel = url

    src_path = UPLOAD_DIR / rel
    if not src_path.exists():
        return {"ok": False, "error": "源文件不存在"}

    # 复制到 gallery 目录
    ext = src_path.suffix or ".jpg"
    new_name = f"portrait_{uuid.uuid4().hex[:8]}{ext}"
    dst_path = GALLERY_DIR / new_name
    shutil.copy2(src_path, dst_path)
    # 复制完成后删除 generated 临时文件
    try:
        src_path.unlink()
    except OSError:
        pass

    # 创建 GalleryImage 记录
    img = GalleryImage(
        filename=new_name,
        filepath=f"/uploads/gallery/{new_name}",
        tag="portrait",
    )
    db.add(img)
    await db.commit()
    await db.refresh(img)

    print(f"{PFX} [保存] ✅ {new_name} → gallery id={img.id[:8]}...", flush=True)

    # 后台分析（提取人脸等）
    if background_tasks:
        from app.api.profile import _run_gallery_analysis
        background_tasks.add_task(_run_gallery_analysis, img.id, dst_path)

    return {"ok": True, "id": img.id, "url": img.filepath}
