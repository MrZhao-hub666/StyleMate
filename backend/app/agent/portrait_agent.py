"""
创意生成 Agent — 链式调用

流程：search trends(可选) → 构建 prompt → LLM 优化 prompt
"""

from app.services.llm_service import get_model
from app.knowledge.loader import get_knowledge_base


async def optimize_prompt(
    user_description: str,
    style: str = "",
    style_profile: str = "",
    has_face: bool = False,
    gender: str = "未设置",
) -> str:
    """
    优化用户描述为高质量生图 prompt

    Args:
        user_description: 用户原始描述
        style: 可选风格提示
        style_profile: 用户风格偏好描述

    Returns:
        优化后的 prompt
    """
    model = get_model(temperature=0.7)

    # 搜索趋势关键词
    trend_str = ""
    if style:
        try:
            kb = get_knowledge_base()
            results = kb.search(f"{style} 风格 趋势", 3)
            trend_str = "\n".join(r["content"][:150] for r in results)[:500]
        except Exception:
            pass

    # 构建系统提示词
    if has_face:
        # 图生图模式：只描述服装和场景，不描述人物外貌
        gender_hint = ""
        if gender in ("男", "男性", "male"):
            gender_hint = "用户为男性，服装描述应使用男装相关用语（如西装、衬衫等）。"
        elif gender in ("女", "女性", "female"):
            gender_hint = "用户为女性，服装描述应使用女装相关用语（如连衣裙、半裙等）。"
        else:
            gender_hint = "请根据用户描述自行判断性别，使用对应服装用语。"

        system_prompt = f"""你是专业 AI 图像编辑 prompt 优化师。
用户的参考照片已提供，你需要优化的是服装和场景描述，不要描述人物外貌。

规则：
1. 只描述服装款式、颜色、材质、图案
2. 只描述背景场景、光线氛围
3. 加入画质词（高清/细腻）
4. 不要描述人物面部、发型、身材等外貌特征
5. {gender_hint}
6. 不超过100字"""
    else:
        # 文生图模式：完整描述
        gender_hint = ""
        if gender in ("男", "男性", "male"):
            gender_hint = "生成男性人物。"
        elif gender in ("女", "女性", "female"):
            gender_hint = "生成女性人物。"
        else:
            gender_hint = "根据描述判断性别。"

        system_prompt = f"""你是专业 AI 生图 prompt 优化师。
把用户需求优化为高质量中文生图 prompt。

规则：
1. 加入构图描述（半身肖像/全身站立）
2. 加入光线描述（自然光/柔光）
3. 加入画质词（高清/细腻）
4. 如果提供了用户风格偏好，请确保生成风格符合用户审美
5. {gender_hint}
6. 不超过150字"""

    context = f"风格参考：{style}\n趋势：{trend_str[:300]}"
    if style_profile:
        context += f"\n{style_profile}"
    context += f"\n\n用户描述：{user_description}\n\n请优化为 prompt："

    response = await model.ainvoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context},
    ])

    return response.content.strip()
