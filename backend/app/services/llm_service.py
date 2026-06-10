"""
LLM 服务 — 统一入口

DeepSeek-v4-flash：搭配推荐、写真 prompt 优化
qwen3.7-plus：穿搭评价、云端视觉精细识别（多模态视觉理解）
"""

from langchain.chat_models import init_chat_model
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from app.config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, DASHSCOPE_VISION_MODEL


def get_model(temperature: float = 0.7, max_tokens: int = 2048):
    """获取 DeepSeek 文本模型实例"""
    return init_chat_model(
        model=DEEPSEEK_MODEL,
        model_provider="openai",
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def get_qwen_vision_model(temperature: float = 0.5, max_tokens: int = 2048):
    """获取 qwen3.7-plus 多模态视觉模型实例（DashScope）"""
    return init_chat_model(
        model=DASHSCOPE_VISION_MODEL,
        model_provider="openai",
        api_key=DASHSCOPE_API_KEY,
        base_url=DASHSCOPE_BASE_URL,
        temperature=temperature,
        max_tokens=max_tokens,
    )
