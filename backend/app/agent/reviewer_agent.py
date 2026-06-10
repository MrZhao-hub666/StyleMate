"""
穿搭评价 Agent — 多模态视觉评价
使用 response_format json_object 强制输出 JSON
"""

import json
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from app.config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, DASHSCOPE_VISION_MODEL
PFX = "[reviewer]"

REVIEW_SYSTEM_PROMPT = """你是专业时尚穿搭顾问。仔细观察照片中的穿搭，从颜色搭配、版型、风格协调、场合适配等维度评价。

以照片中看到的为准。"""  # noqa


def _get_review_model():
    return init_chat_model(
        model=DASHSCOPE_VISION_MODEL,
        model_provider="openai",
        api_key=DASHSCOPE_API_KEY,
        base_url=DASHSCOPE_BASE_URL,
        temperature=0,
        max_tokens=1024,
    )


async def review_outfit(
    image_base64: str,
    edge_attributes: dict | None = None,
    occasion: str = "日常休闲",
    style_profile: str = "",
) -> dict:
    edge_hint = ""
    if edge_attributes:
        edge_hint = f"\n（注：以下机器自动检测数据仅供参考，常因光线角度不准，以你视觉为准：{edge_attributes.get('category','')}，{edge_attributes.get('primary_color_name','')}色，{edge_attributes.get('pattern','')}，{edge_attributes.get('fabric','')}）"

    style_hint = ""
    if style_profile:
        style_hint = f"\n（用户日常穿搭偏好：{style_profile[:80]}，仅供参考）"

    img_url = image_base64
    if not img_url.startswith("data:image/"):
        img_url = f"data:image/jpeg;base64,{img_url}"

    print(f"{PFX} 开始评价: model={DASHSCOPE_VISION_MODEL} occasion={occasion} img_len={len(image_base64)}", flush=True)

    user_text = f"场合：{occasion}{style_hint}{edge_hint}\n\n请评价这身穿搭，输出 JSON：{{\"score\": 7, \"summary\": \"总评\", \"highlights\": [\"亮点\"], \"weaknesses\": [\"不足\"], \"suggestions\": [\"建议\"]}}"

    model = _get_review_model()
    response = await model.ainvoke(
        [
            {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
            HumanMessage(content=[
                {"type": "image_url", "image_url": {"url": img_url}},
                {"type": "text", "text": user_text},
            ]),
        ],
        response_format={"type": "json_object"},
    )

    raw = response.content.strip()
    print(f"{PFX} 响应 length={len(raw)}", flush=True)

    try:
        data = json.loads(raw)
        print(f"{PFX} ✅ score={data.get('score')}", flush=True)
        return data
    except json.JSONDecodeError:
        print(f"{PFX} ❌ JSON解析失败, raw[:200]={raw[:200]}", flush=True)
        return {
            "score": 5,
            "summary": raw[:300] if raw else "解析失败",
            "highlights": [],
            "weaknesses": [],
            "suggestions": [],
        }
