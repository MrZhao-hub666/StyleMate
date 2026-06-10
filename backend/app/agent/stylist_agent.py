"""
搭配推荐 Agent

流程：并行获取天气+知识 → 构建 prompt → LLM 生成方案
使用 async 函数串联，无额外编排框架依赖。
"""

import json
import asyncio
from app.services.llm_service import get_model
from app.knowledge.loader import get_knowledge_base
from app.services.weather_service import get_current_weather


async def recommend_outfit(
    occasion: str,
    preference: str = "",
    city: str = "北京",
    wardrobe_items: list[dict] = None,
    style_profile: str = "",
) -> dict:
    """
    智能搭配推荐

    1. 并行获取天气 + 知识库
    2. 构建上下文 prompt
    3. LLM 生成 3 套方案 → JSON 解析
    """
    wardrobe = wardrobe_items or []

    # === Phase 1: 并行获取上下文 ===
    weather_task = get_current_weather(city)
    kb = get_knowledge_base()
    knowledge_task = asyncio.to_thread(
        kb.search, f"{occasion} 穿搭建议 色彩搭配 款式推荐", 5
    )
    weather, knowledge_results = await asyncio.gather(weather_task, knowledge_task)
    knowledge = "\n\n".join(
        f"[{r['source']}] {r['content']}" for r in knowledge_results
    )

    # === Phase 2: 构建 prompt ===
    if wardrobe:
        wardrobe_desc = json.dumps(wardrobe[:20], ensure_ascii=False)
        user_msg = f"""用户衣橱中的衣物：
{wardrobe_desc}

{style_profile}

场合：{occasion}
天气：{json.dumps(weather, ensure_ascii=False)}
用户偏好描述：{preference or '无'}
知识：{knowledge[:800]}

请严格参考用户的风格偏好数据（颜色倾向、图案喜好、品类偏好、风格倾向），从衣橱中选择最符合用户审美的衣物，生成3套搭配方案。JSON数组格式：
[{{"name": "方案名", "items": [...], "reason": "推荐理由（需提及为何符合用户风格偏好）"}}]"""
    else:
        user_msg = f"""场合：{occasion}
天气：{json.dumps(weather, ensure_ascii=False)}
{style_profile}
知识：{knowledge[:1200]}

请结合用户风格偏好，生成3套通用穿搭建议，JSON格式：
[{{"name": "方案名", "items": ["上装", "下装", "鞋履"], "reason": "理由"}}]"""

    system_prompt = "你是专业时尚搭配师。请严格参考用户风格偏好数据，确保推荐符合用户的颜色和风格倾向。输出 JSON 数组。"

    # === Phase 3: LLM 推理 ===
    model = get_model(temperature=0.7)
    response = await model.ainvoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ])

    # === Phase 4: 解析 ===
    cleaned = response.content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        candidates = json.loads(cleaned)
    except json.JSONDecodeError:
        candidates = [{"name": "推荐方案", "items": [], "reason": response.content[:200]}]

    return {
        "occasion": occasion,
        "weather": weather,
        "recommendations": candidates[:3],
    }
