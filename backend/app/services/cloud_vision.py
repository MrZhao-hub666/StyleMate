"""
云端视觉分析服务 — qwen3.7-plus 多模态精细识别

流程：边端YOLO属性(参考) + 原始裁剪图 → qwen3.7-plus 看图验证 → 返回完整7维属性
"""

import json
from langchain_core.messages import HumanMessage
from app.services.llm_service import get_qwen_vision_model


async def infer_clothing_details(edge_attrs: dict, crop_base64: str = "") -> dict:
    """
    基于边端YOLO属性 + 裁剪原图，qwen3.7-plus 看图精细识别

    Args:
        edge_attrs: 边端YOLO分析结果
            {zone, category, primary_color_name, primary_color_hex, pattern,
             fabric, length_category, secondary_color_name, ...}
        crop_base64: 衣物裁剪图base64（不含data:前缀）

    Returns:
        {subcategory, neckline, sleeve, fit, 以及校验后的颜色/图案/面料/长度}
    """
    model = get_qwen_vision_model(temperature=0.3, max_tokens=400)

    # YOLO属性作为参考文本
    yolo_ref = {k: v for k, v in edge_attrs.items()
                if k not in ("crop_base64", "face_crop_base64", "bbox", "source_image")}
    yolo_text = json.dumps(yolo_ref, ensure_ascii=False, indent=2)

    system_prompt = """你是专业的服装视觉分析专家。请仔细观察图片中的衣物，结合参考数据进行校验和修正。

分析维度：
1. 品类子类（如：圆领T恤、牛仔裤、运动鞋、风衣、连衣裙，需具体细化）
2. 主色名称和HEX（以视觉为准，YOLO仅供参考）
3. 辅色名称和HEX
4. 图案类型（纯色/条纹/格子/印花/碎花/渐变/迷彩）
5. 面料材质（棉质/牛仔/丝绸/皮革/针织/化纤混纺）
6. 长度类别（短款/及腰/盖臀/及膝/七分九分/全长）
7. 版型（修身/宽松/直筒/紧身/阔腿）
8. 领型（仅上装：圆领/V领/翻领/立领/无领/pending_cloud）
9. 袖长（仅上装：短袖/长袖/无袖/七分袖/pending_cloud）

原则：以你看到的图片为准，YOLO数据如有偏差请修正。仅输出 JSON。"""
    if not crop_base64:
        return _fallback(edge_attrs)

    img_url = crop_base64 if crop_base64.startswith("data:image/") else f"data:image/jpeg;base64,{crop_base64}"

    user_msg = f"""请观察这件衣物的图片，分析全部属性。

边端YOLO自动分析数据（仅供参考，以你的视觉判断为准）：
{yolo_text}

输出 JSON：
{{"subcategory":"...","primary_color_name":"...","primary_color_hex":"...","secondary_color_name":"...","secondary_color_hex":"...","pattern":"...","fabric":"...","length_category":"...","fit":"...","neckline":"...","sleeve":"..."}}"""

    response = await model.ainvoke([
        {"role": "system", "content": system_prompt},
        HumanMessage(content=[
            {"type": "image_url", "image_url": {"url": img_url}},
            {"type": "text", "text": user_msg},
        ]),
    ])

    cleaned = response.content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        result = json.loads(cleaned)
        # 合并：Qwen返回的覆盖YOLO，未返回的保留YOLO原始值
        merged = {
            "subcategory": result.get("subcategory", edge_attrs.get("subcategory", "pending_cloud")),
            "primary_color_name": result.get("primary_color_name", edge_attrs.get("primary_color_name", "未知")),
            "primary_color_hex": result.get("primary_color_hex", edge_attrs.get("primary_color_hex", "#808080")),
            "secondary_color_name": result.get("secondary_color_name", edge_attrs.get("secondary_color_name")),
            "secondary_color_hex": result.get("secondary_color_hex", edge_attrs.get("secondary_color_hex")),
            "pattern": result.get("pattern", edge_attrs.get("pattern", "未知")),
            "fabric": result.get("fabric", edge_attrs.get("fabric", "未知")),
            "length_category": result.get("length_category", edge_attrs.get("length_category", "未知")),
            "fit": result.get("fit", edge_attrs.get("fit", "pending_cloud")),
            "neckline": result.get("neckline", edge_attrs.get("neckline", "pending_cloud")),
            "sleeve": result.get("sleeve", edge_attrs.get("sleeve", "pending_cloud")),
        }
        return merged
    except json.JSONDecodeError:
        return _fallback(edge_attrs)


def _fallback(edge_attrs: dict) -> dict:
    """Qwen不可用时，保留YOLO原始值"""
    return {
        "subcategory": edge_attrs.get("subcategory", "pending_cloud"),
        "primary_color_name": edge_attrs.get("primary_color_name", "未知"),
        "primary_color_hex": edge_attrs.get("primary_color_hex", "#808080"),
        "secondary_color_name": edge_attrs.get("secondary_color_name"),
        "secondary_color_hex": edge_attrs.get("secondary_color_hex"),
        "pattern": edge_attrs.get("pattern", "未知"),
        "fabric": edge_attrs.get("fabric", "未知"),
        "length_category": edge_attrs.get("length_category", "未知"),
        "fit": edge_attrs.get("fit", "pending_cloud"),
        "neckline": edge_attrs.get("neckline", "pending_cloud"),
        "sleeve": edge_attrs.get("sleeve", "pending_cloud"),
    }
