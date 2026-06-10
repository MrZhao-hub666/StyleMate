"""
衣物品类标识模块

边端不依赖 ImageNet 分类模型做细粒度识别。
只做基本的区域→品类推断（upper→上装，lower→下装等），
品类细分类/领型/袖长/版型交由云端视觉 LLM 完成。
"""

# 基础的区域→品类推断（纯启发式，不依赖深度学习）
ZONE_TO_CATEGORY = {
    "upper": "上装",
    "lower": "下装",
    "full": "全身穿搭",
    "single_garment": "衣物",
    "shoes": "鞋履",
}


class ClothingClassifier:
    """
    轻量级品类标识器

    不做深度模型推理，只做基于区域的品类推断。
    """

    def __init__(self):
        self.source = "edge_heuristic"

    def classify_category(self, zone: str = "single_garment") -> dict:
        """
        基于区域推断品类大类

        Returns:
            {"category": str, "subcategory": str, "source": "edge_heuristic"}
        """
        category = ZONE_TO_CATEGORY.get(zone, "未知")
        return {
            "category": category,
            "subcategory": "pending_cloud",
            "source": self.source,
        }
