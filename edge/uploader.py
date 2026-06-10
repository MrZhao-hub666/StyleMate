"""
HTTP 数据上传模块

将边端 YOLO 解析后的结构化数据 + 裁剪图(base64)上传到云端 API。
"""

import requests
from dataclasses import asdict
from attribute_pipeline import ClothingAttribute


class CloudUploader:
    """云端数据上传客户端"""

    def __init__(self, base_url: str = "http://localhost:9000", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = min(timeout, 300)  # 上限 5 分钟
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "StyleMate-Edge/1.0",
        })

    def upload_batch(self, attrs: list[ClothingAttribute]) -> dict:
        """
        批量上传衣物

        Returns:
            dict: {"success": int, "failed": int, "items": [...]}
        """
        payload = {
            "clothing_items": [asdict(a) for a in attrs],
            "needs_cloud_vision": True,
        }
        batch_timeout = min(self.timeout * len(attrs) + 30, 600)  # 上限 10 分钟
        resp = self.session.post(
            f"{self.base_url}/api/edge/upload/batch",
            json=payload,
            timeout=batch_timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def health_check(self) -> bool:
        """健康检查"""
        try:
            resp = self.session.get(
                f"{self.base_url}/api/health",
                timeout=5,
            )
            return resp.status_code == 200
        except requests.RequestException:
            return False
