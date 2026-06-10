"""
磁盘清理服务
每次后端启动时清理 /uploads/generated/ 下超过 1 小时的临时文件
"""

import time
from pathlib import Path
from app.config import UPLOAD_DIR

GENERATED_DIR = UPLOAD_DIR / "generated"
MAX_AGE_SECONDS = 3600  # 1 小时


def cleanup_generated():
    """删除 /generated/ 下超过 1 小时的孤儿文件"""
    GENERATED_DIR.mkdir(exist_ok=True)
    now = time.time()
    deleted = 0
    for f in GENERATED_DIR.iterdir():
        if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png"):
            age = now - f.stat().st_mtime
            if age > MAX_AGE_SECONDS:
                try:
                    f.unlink()
                    deleted += 1
                except OSError:
                    pass
    if deleted:
        print(f"[cleanup] 清理 {deleted} 个过期生成文件", flush=True)
