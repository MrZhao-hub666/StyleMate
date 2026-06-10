"""
用户风格画像服务 — 聚合相册+衣橱数据，生成颜色/图案/品类偏好，供 LLM prompt 注入
"""

import base64
import httpx
from collections import Counter
from datetime import datetime

# 边端分析服务地址（本地 localhost:9001）
_EDGE_URL = "http://localhost:9001/analyze"
_PFX = "[style_profiler]"


def _analyze_photo_with_edge_pipeline(image_path: str) -> dict:
    """
    通过 HTTP 调用边端分析服务分析单张照片

    Returns:
        {
            "has_person": bool,
            "person_count": int,
            "colors": [{"name":"黑色","hex":"#1a1a2e","ratio":0.45}, ...],
            "categories": ["上装","下装"],
            "dominant_pattern": "纯色",
            "face_crop_b64": "data:image/jpeg;base64,..." 或 None
        }
    """
    try:
        # 读取图片文件 → base64（后端无 opencv，纯 Python 实现）
        print(f"{_PFX} [分析] 读取照片: {image_path}", flush=True)
        with open(image_path, "rb") as f:
            img_bytes = f.read()
        b64 = base64.b64encode(img_bytes).decode()
        print(f"{_PFX} [分析] 文件={len(img_bytes)}bytes → base64={len(b64)}字符", flush=True)

        # 调用边端 HTTP 服务
        print(f"{_PFX} [分析] 发送到边端 {_EDGE_URL}...", flush=True)
        resp = httpx.post(
            _EDGE_URL,
            json={"image_base64": b64, "zone": "portrait"},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

        print(f"{_PFX} [分析] 边端返回: has_person={data.get('has_person')} face={bool(data.get('face_crop_base64'))} colors={data.get('primary_color_name')}", flush=True)

        # 转换为统一格式
        colors = []
        if data.get("primary_color_name") and data["primary_color_name"] != "未知":
            colors.append({
                "name": data["primary_color_name"],
                "hex": data["primary_color_hex"],
                "ratio": data.get("primary_color_ratio", 1.0),
            })
            if data.get("secondary_color_name") and data["secondary_color_name"] != "未知":
                colors.append({
                    "name": data["secondary_color_name"],
                    "hex": data["secondary_color_hex"],
                    "ratio": data.get("secondary_color_ratio", 0.0),
                })

        categories = []
        cat = data.get("category", "")
        if cat and cat != "未知":
            categories.append(cat)

        return {
            "has_person": data.get("has_person", False),
            "person_count": 1 if data.get("has_person") else 0,
            "colors": colors,
            "categories": categories,
            "dominant_pattern": data.get("pattern", "未知"),
            "face_crop_b64": data.get("face_crop_base64"),
        }

    except httpx.ConnectError as e:
        print(f"{_PFX} [分析] ❌ 边端连接失败: {e}", flush=True)
        return {"has_person": False, "person_count": 0, "error": f"边端服务不可用: {e}"}
    except Exception as e:
        print(f"{_PFX} [分析] ❌ 异常: {e}", flush=True)
        return {"has_person": False, "person_count": 0, "error": str(e)}


def analyze_gallery_photo(image_path: str) -> dict:
    """
    分析单张相册照片（对外接口）

    优先使用边端YOLO管线，不可用时返回基础信息。
    """
    result = _analyze_photo_with_edge_pipeline(image_path)

    if "error" in result:
        # 边端不可用时返回空结构，聚合时仅依赖衣橱数据
        return {
            "has_person": False,
            "person_count": 0,
            "colors": [],
            "categories": [],
            "dominant_pattern": "未知",
            "face_crop_b64": None,
            "error": result["error"],
        }

    return result


def _normalize_color_name(name: str) -> str:
    """将具体颜色名归并到色系大类（如"深蓝"→"蓝色系"）"""
    color_groups = {
        "黑色": ["纯黑", "暗灰", "深灰", "黑"],
        "白色": ["纯白", "亮灰", "浅灰", "白"],
        "灰色": ["灰色", "灰", "浅灰"],
        "蓝色系": ["蓝色", "深蓝", "蓝青", "浅蓝", "蓝", "靛蓝", "暗蓝", "亮蓝"],
        "红色系": ["红色", "深红", "橙红", "紫红", "粉红", "品红", "红", "暗红"],
        "绿色系": ["绿色", "深绿", "青绿", "黄绿", "绿"],
        "棕色系": ["棕色", "咖啡", "褐色", "驼色", "米色", "卡其"],
        "黄色系": ["黄色", "黄橙", "橙色", "金黄", "暗黄"],
        "紫色系": ["紫色", "深紫", "蓝紫", "紫"],
    }
    for group_name, names in color_groups.items():
        if name in names or name == group_name:
            return group_name
    return name


def _time_weight(days_old: float | None) -> float:
    """
    时间衰减权重：越近期的数据权重越高

    ≤7天：1.0    |  8-30天：0.8   |  31-90天：0.5
    91-365天：0.3 |  >365天：0.15  |  无时间戳：0.5（兜底）
    """
    if days_old is None:
        return 0.5
    if days_old <= 7:
        return 1.0
    if days_old <= 30:
        return 0.8
    if days_old <= 90:
        return 0.5
    if days_old <= 365:
        return 0.3
    return 0.15


def _days_since(ts: str | None) -> float | None:
    """计算距今天数，无法解析返回 None"""
    if not ts:
        return None
    try:
        from datetime import datetime, timezone
        if isinstance(ts, datetime):
            dt = ts
        else:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (now - dt).total_seconds() / 86400
    except Exception:
        return None


def build_style_profile(
    gallery_analyses: list[dict],
    wardrobe_items: list[dict],
) -> dict:
    """
    聚合相册分析 + 衣橱数据 → 用户风格画像（带时间衰减）

    每张照片/每件衣物的贡献乘以 _time_weight() 时间衰减系数。

    Args:
        gallery_analyses: GalleryImageAnalysis 记录列表
            (含 colors/categories/patterns + analyzed_at 时间戳)
        wardrobe_items: Clothing 表记录列表
            (含 color/pattern/category + created_at 时间戳)

    Returns:
        UserStyleProfile 数据 dict
    """
    # === 颜色偏好统计 ===
    color_counter = Counter()

    for a in gallery_analyses:
        w = _time_weight(_days_since(a.get("analyzed_at")))
        for c in (a.get("clothing_colors") or []):
            name = _normalize_color_name(c.get("name", ""))
            color_counter[name] += c.get("ratio", 0) * w

    for wi in wardrobe_items:
        w = _time_weight(_days_since(wi.get("created_at")))
        pn = wi.get("primary_color_name", "")
        if pn and pn != "未知":
            color_counter[_normalize_color_name(pn)] += 0.5 * w
        sn = wi.get("secondary_color_name", "")
        if sn and sn != "未知":
            color_counter[_normalize_color_name(sn)] += 0.2 * w

    total_color = sum(color_counter.values()) or 1
    color_prefs = sorted(
        [{"color": k, "ratio": round(v / total_color, 3)} for k, v in color_counter.items()],
        key=lambda x: x["ratio"], reverse=True
    )[:6]

    # === 图案偏好统计 ===
    pattern_counter = Counter()
    for a in gallery_analyses:
        w = _time_weight(_days_since(a.get("analyzed_at")))
        dp = a.get("dominant_pattern", "")
        if dp and dp != "未知":
            pattern_counter[dp] += 1 * w
    for wi in wardrobe_items:
        w = _time_weight(_days_since(wi.get("created_at")))
        p = wi.get("pattern", "")
        if p and p != "未知":
            pattern_counter[p] += 1 * w

    total_pattern = sum(pattern_counter.values()) or 1
    pattern_prefs = {k: round(v / total_pattern, 3) for k, v in pattern_counter.most_common(8)}

    # === 品类偏好统计 ===
    cat_counter = Counter()
    for a in gallery_analyses:
        w = _time_weight(_days_since(a.get("analyzed_at")))
        for cat in (a.get("clothing_categories") or []):
            cat_counter[cat] += 1 * w
    for wi in wardrobe_items:
        w = _time_weight(_days_since(wi.get("created_at")))
        cat = wi.get("category", "")
        if cat and cat != "未知":
            cat_counter[cat] += 1 * w

    total_cat = sum(cat_counter.values()) or 1
    cat_prefs = {k: round(v / total_cat, 3) for k, v in cat_counter.most_common(6)}

    # === 主导色HEX ===
    hex_counter = Counter()
    for a in gallery_analyses:
        w = _time_weight(_days_since(a.get("analyzed_at")))
        for c in (a.get("clothing_colors") or []):
            h = c.get("hex", "")
            if h:
                hex_counter[h] += c.get("ratio", 0) * w
    for wi in wardrobe_items:
        w = _time_weight(_days_since(wi.get("created_at")))
        h = wi.get("primary_color_hex", "")
        if h and h != "#808080":
            hex_counter[h] += 0.5 * w

    dominant_hex = [h for h, _ in hex_counter.most_common(5)]

    # === 风格倾向推断 ===
    tendency = _infer_style_tendency(color_prefs, pattern_prefs, cat_prefs)

    # === 置信度 ===
    sample_count = len(gallery_analyses) + len(wardrobe_items)
    confidence = min(0.95, 0.3 + sample_count * 0.03)

    return {
        "color_preferences": color_prefs,
        "pattern_preferences": pattern_prefs,
        "category_preferences": cat_prefs,
        "style_tendency": tendency,
        "dominant_colors_hex": dominant_hex,
        "gallery_photo_count": len(gallery_analyses),
        "wardrobe_item_count": len(wardrobe_items),
        "confidence": round(confidence, 3),
    }


def _infer_style_tendency(
    color_prefs: list[dict],
    pattern_prefs: dict,
    cat_prefs: dict,
) -> str:
    """基于颜色+图案+品类推断风格倾向（启发式规则）"""
    top_colors = [c["color"] for c in color_prefs[:3]] if color_prefs else []
    top_pattern = max(pattern_prefs, key=pattern_prefs.get) if pattern_prefs else "纯色"
    top_cat = max(cat_prefs, key=cat_prefs.get) if cat_prefs else ""

    # 暗色系主导 → 简约/商务/都市
    dark_colors = {"黑色", "灰色", "蓝色系"}
    warm_colors = {"红色系", "橙色", "黄色系", "棕色系", "粉色"}
    light_colors = {"白色", "浅蓝", "浅灰"}

    dark_count = sum(1 for c in top_colors if c in dark_colors)
    warm_count = sum(1 for c in top_colors if c in warm_colors)

    if dark_count >= 2 and top_pattern == "纯色":
        if top_cat in ("上装", "全身穿搭"):
            return "简约都市风"
        return "极简冷淡风"
    elif warm_count >= 2:
        return "温暖休闲风"
    elif top_pattern in ("印花/碎花", "格子"):
        return "复古文艺风"
    elif "运动" in str(cat_prefs) or top_cat == "鞋履":
        return "运动休闲风"
    elif top_cat == "全身穿搭":
        return "精致通勤风"
    else:
        return "混搭个性风"


async def get_style_prompt(db) -> str:
    """
    从数据库读取用户风格画像并格式化为 LLM prompt 文本。
    供 portrait/recommend/review 等接口复用。
    """
    from sqlalchemy import select
    from app.models.user import UserStyleProfile

    stmt = select(UserStyleProfile).limit(1)
    r = await db.execute(stmt)
    style = r.scalar_one_or_none()
    if not style:
        return ""

    profile = {
        "color_preferences": style.color_preferences,
        "pattern_preferences": style.pattern_preferences,
        "category_preferences": style.category_preferences,
        "style_tendency": style.style_tendency,
        "dominant_colors_hex": style.dominant_colors_hex,
        "gallery_photo_count": style.gallery_photo_count,
        "wardrobe_item_count": style.wardrobe_item_count,
        "confidence": style.confidence,
    }
    return format_style_for_llm(profile)


def format_style_for_llm(profile: dict) -> str:
    """
    将风格画像格式化为 LLM prompt 可用的自然语言描述
    """
    if not profile or profile.get("confidence", 0) < 0.2:
        return "（用户风格画像数据不足，可参考通用搭配建议）"

    lines = [
        "## 用户穿搭风格偏好（基于历史照片和衣橱数据分析，近期数据权重更高）\n",
        "注意：以下偏好已应用时间衰减——近一周数据权重1.0，近一月0.8，三个月内0.5，一年内0.3，超过一年仅作辅助参考。\n",
    ]

    # 颜色偏好
    colors = profile.get("color_preferences", [])
    if colors:
        color_desc = "、".join(
            f"{c['color']}({int(c['ratio']*100)}%)" for c in colors[:4]
        )
        lines.append(f"偏好色系：{color_desc}")

    # 图案偏好
    patterns = profile.get("pattern_preferences", {})
    if patterns:
        top_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:3]
        p_desc = "、".join(f"{k}({int(v*100)}%)" for k, v in top_patterns)
        lines.append(f"偏好图案：{p_desc}")

    # 品类偏好
    cats = profile.get("category_preferences", {})
    if cats:
        top_cats = sorted(cats.items(), key=lambda x: x[1], reverse=True)[:3]
        c_desc = "、".join(f"{k}({int(v*100)}%)" for k, v in top_cats)
        lines.append(f"偏好品类：{c_desc}")

    # 风格倾向
    tendency = profile.get("style_tendency", "")
    if tendency:
        lines.append(f"风格倾向：{tendency}")

    confidence = profile.get("confidence", 0)
    lines.append(f"数据置信度：{int(confidence*100)}%（基于{profile.get('gallery_photo_count', 0)}张相册照片和{profile.get('wardrobe_item_count', 0)}件衣橱物品）")

    return "\n".join(lines)


# ====== DB 操作（需 import 异步——延迟导入避免循环依赖） ======

async def rebuild_style_profile(db):
    """
    从数据库聚合所有数据，重建用户风格画像（Upsert）

    供 profile.py / wardrobe.py 的增删改接口调用。
    """
    from sqlalchemy import select
    from app.models.user import GalleryImageAnalysis, UserStyleProfile
    from app.models.clothing import Clothing

    # 查询所有分析结果
    stmt = select(GalleryImageAnalysis).where(GalleryImageAnalysis.analyzed == True)
    r = await db.execute(stmt)
    analyses = [
        {
            "clothing_colors": a.clothing_colors or [],
            "clothing_categories": a.clothing_categories or [],
            "dominant_pattern": a.dominant_pattern,
            "analyzed_at": str(a.analyzed_at) if a.analyzed_at else None,
        }
        for a in r.scalars().all()
    ]

    # 查询衣橱
    stmt2 = select(Clothing)
    r2 = await db.execute(stmt2)
    wardrobe = [
        {
            "primary_color_name": c.primary_color_name,
            "primary_color_hex": c.primary_color_hex,
            "secondary_color_name": c.secondary_color_name,
            "secondary_color_hex": c.secondary_color_hex,
            "pattern": c.pattern,
            "category": c.category,
            "created_at": str(c.created_at) if c.created_at else None,
        }
        for c in r2.scalars().all()
    ]

    # 构建画像
    profile_data = build_style_profile(analyses, wardrobe)

    # Upsert
    stmt3 = select(UserStyleProfile).limit(1)
    r3 = await db.execute(stmt3)
    existing = r3.scalar_one_or_none()

    if existing:
        existing.color_preferences = profile_data["color_preferences"]
        existing.pattern_preferences = profile_data["pattern_preferences"]
        existing.category_preferences = profile_data["category_preferences"]
        existing.style_tendency = profile_data["style_tendency"]
        existing.dominant_colors_hex = profile_data["dominant_colors_hex"]
        existing.gallery_photo_count = profile_data["gallery_photo_count"]
        existing.wardrobe_item_count = profile_data["wardrobe_item_count"]
        existing.confidence = profile_data["confidence"]
    else:
        existing = UserStyleProfile(**profile_data)
        db.add(existing)

    return existing
