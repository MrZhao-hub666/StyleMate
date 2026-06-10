"""
StyleMate 后端配置

读取优先级：系统环境变量 > .env 文件
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 加载 .env
load_dotenv(BASE_DIR / ".env")

# ====== DeepSeek API ======
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = "deepseek-v4-flash"

# ====== 可选 API ======
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
DASHSCOPE_VISION_MODEL = "qwen3-vl-flash"
DASHSCOPE_IMAGE_MODEL = "wan2.7-image"
DASHSCOPE_IMAGE_MODEL_PRO = "wan2.7-image-pro"

# ====== 数据库 ======
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{BASE_DIR / 'stylemate.db'}")
DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"


# ====== 知识库 ======
CHROMA_PERSIST_DIR = str(BASE_DIR / "chroma_db")

# ====== 服务器 ======
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "9000"))

# ====== 上传文件 ======
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
