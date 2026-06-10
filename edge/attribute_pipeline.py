"""
七维属性解析主管线

边端即时输出：
  ① 品类大类（启发式：upper/lower/shoes → 上装/下装/鞋履）
  ② 颜色（K-means 主色+辅色，HSV 自动命名）
  ③ 图案（Gabor+频谱分析）
  ④ 长度比例（宽高比估算）
  ⑤ 材质推测（纹理+光泽度）
  ⑥ 裁剪图 base64（供云端视觉识别使用）

待云端补充：
  ① 品类细分类 → pending_cloud
  ② 款式（领型/袖长/版型） → pending_cloud

每个 ClothingAttribute 自带 needs_cloud 标记和 crop_base64。
"""

import cv2
import base64
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from detector import ClothingDetector
from classifier import ClothingClassifier
from color_analyzer import ColorAnalyzer
from texture_analyzer import TextureAnalyzer


@dataclass
class ClothingAttribute:
    """衣物属性数据结构（七维，含云端待补充标记）"""
    id: Optional[str] = None

    # ① 品类
    category: str = "未知"           # 上装 / 下装 / 全身穿搭 / 衣物
    subcategory: str = "pending_cloud"
    category_source: str = "edge_heuristic"

    # ② 颜色
    primary_color_hex: str = "#808080"
    primary_color_name: str = "未知"
    primary_color_ratio: float = 0.0
    secondary_color_hex: Optional[str] = None
    secondary_color_name: Optional[str] = None
    secondary_color_ratio: float = 0.0

    # ③ 图案
    pattern: str = "未知"
    pattern_confidence: float = 0.0

    # ④ 款式（待云端）
    neckline: str = "pending_cloud"
    sleeve: str = "pending_cloud"
    fit: str = "pending_cloud"

    # ⑤ 长度比例
    length_category: str = "未知"

    # ⑥ 材质
    fabric: str = "未知"
    fabric_confidence: float = 0.0
    glossiness: float = 0.0

    # ⑦ 图像（供云端视觉识别）
    crop_base64: Optional[str] = None

    # 元数据
    zone: str = "single_garment"
    bbox: Optional[tuple] = None
    has_person: bool = False
    needs_cloud: bool = True         # 是否需要云端补充
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    source_image: str = ""


class AttributePipeline:
    """七维属性解析管线（边端即时 + 云端待补充）"""

    def __init__(self, device: str = "cpu"):
        self.detector = ClothingDetector(device=device)
        self.classifier = ClothingClassifier()
        self.color_analyzer = ColorAnalyzer()
        self.texture_analyzer = TextureAnalyzer()

    def _encode_crop(self, image: np.ndarray, quality: int = 85) -> str:
        """裁剪图 → base64"""
        success, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if not success:
            return ""
        return base64.b64encode(buffer).decode("utf-8")

    def _estimate_length(self, crop: np.ndarray, zone: str) -> str:
        """宽高比估算长度类别"""
        if crop is None or crop.size == 0:
            return "未知"
        h, w = crop.shape[:2]
        ratio = h / w if w > 0 else 0

        if zone == "shoes":
            return "鞋履"
        elif zone == "upper":
            if ratio < 0.6:   return "露脐款"
            elif ratio < 0.9: return "及腰"
            elif ratio < 1.4: return "盖臀"
            else:             return "中长款"
        elif zone == "lower":
            if ratio < 0.5:   return "超短款"
            elif ratio < 0.8: return "短款"
            elif ratio < 1.2: return "及膝"
            elif ratio < 1.8: return "七分/九分"
            else:             return "全长"
        else:
            if ratio < 0.7:   return "短款"
            elif ratio < 1.3: return "标准"
            else:             return "长款"

    def analyze_region(self, crop: np.ndarray, zone: str,
                       has_person: bool = False,
                       mask: np.ndarray = None) -> ClothingAttribute:
        """
        对单个区域执行边端解析

        Args:
            mask: 该区域的前景mask（过滤背景用）
        """
        attr = ClothingAttribute()
        attr.zone = zone
        attr.has_person = has_person

        # ====== ① 品类（启发式） ======
        cat_result = self.classifier.classify_category(zone)
        attr.category = cat_result["category"]
        attr.subcategory = cat_result["subcategory"]
        attr.category_source = cat_result["source"]

        # ====== ② 颜色（带mask过滤背景） ======
        colors = self.color_analyzer.extract_colors(crop, mask=mask)
        if colors:
            attr.primary_color_hex = colors[0]["hex"]
            attr.primary_color_name = colors[0]["name"]
            attr.primary_color_ratio = colors[0]["ratio"]
            if len(colors) > 1:
                attr.secondary_color_hex = colors[1]["hex"]
                attr.secondary_color_name = colors[1]["name"]
                attr.secondary_color_ratio = colors[1]["ratio"]

        # ====== ③ 图案 + ⑥ 材质 ======
        tex = self.texture_analyzer.analyze(crop)
        attr.pattern = tex["pattern"]
        attr.pattern_confidence = tex["pattern_confidence"]
        attr.fabric = tex["fabric"]
        attr.fabric_confidence = tex["fabric_confidence"]
        attr.glossiness = tex["glossiness"]

        # ====== ④ 款式 — 标记 pending_cloud ======

        # ====== ⑤ 长度 ======
        attr.length_category = self._estimate_length(crop, zone)

        # ====== ⑦ 裁剪图编码 ======
        attr.crop_base64 = self._encode_crop(crop)

        # ====== 云端补充标记 ======
        attr.needs_cloud = True

        return attr

    def process_frame(self, frame: np.ndarray, source: str = "camera") -> list[ClothingAttribute]:
        """处理摄像头/图片帧"""
        crops = self.detector.extract_clothing_crops(frame)
        results = []

        for crop_info in crops:
            crop = crop_info["crop"]
            if crop is None or crop.size == 0:
                continue
            attr = self.analyze_region(
                crop,
                zone=crop_info["zone"],
                has_person=crop_info.get("has_person", False),
                mask=crop_info.get("mask"),
            )
            attr.bbox = tuple(crop_info["bbox"])
            attr.source_image = source
            results.append(attr)

        return results

    def process_image_file(self, filepath: str) -> list[ClothingAttribute]:
        """处理图片文件"""
        frame = cv2.imread(filepath)
        if frame is None:
            raise FileNotFoundError(f"无法读取图片: {filepath}")
        return self.process_frame(frame, source=filepath)

    def process_single_garment(self, crop: np.ndarray) -> ClothingAttribute:
        """处理单件衣物图片"""
        return self.analyze_region(crop, zone="single_garment")
