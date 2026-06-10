"""
K-means 颜色提取模块（HSV 自动命名）

HEX 由 K-means 聚类精确计算，颜色名由 HSV 色彩空间自动生成。
支持传入 mask 过滤背景，提高衣物区域颜色分析精度。
"""

import cv2
import numpy as np
from sklearn.cluster import KMeans


class ColorAnalyzer:
    """衣物颜色分析器 — HSV 自动命名"""

    # 色相区间定义（0-360° → 颜色名）
    HUE_RANGES = [
        ((0, 12),    "红"),
        ((12, 25),   "橙红"),
        ((25, 40),   "橙色"),
        ((40, 55),   "黄橙"),
        ((55, 70),   "黄色"),
        ((70, 85),   "黄绿"),
        ((85, 100),  "绿色"),
        ((100, 130), "青绿"),
        ((130, 160), "青色"),
        ((160, 190), "蓝青"),
        ((190, 225), "蓝色"),
        ((225, 245), "蓝紫"),
        ((245, 280), "紫色"),
        ((280, 305), "紫红"),
        ((305, 330), "品红"),
        ((330, 348), "粉红"),
        ((348, 360), "红"),
    ]

    def __init__(self, n_colors: int = 5, min_ratio: float = 0.08):
        self.n_colors = n_colors
        self.min_ratio = min_ratio

    def _rgb_to_hsv(self, r: int, g: int, b: int) -> tuple:
        """RGB(0-255) → (H:0-360, S:0-100, V:0-100)"""
        r_n, g_n, b_n = r / 255.0, g / 255.0, b / 255.0
        max_c = max(r_n, g_n, b_n)
        min_c = min(r_n, g_n, b_n)
        delta = max_c - min_c

        # Hue
        h = 0.0
        if delta > 0:
            if max_c == r_n:
                h = 60 * (((g_n - b_n) / delta) % 6)
            elif max_c == g_n:
                h = 60 * (((b_n - r_n) / delta) + 2)
            else:
                h = 60 * (((r_n - g_n) / delta) + 4)
        if h < 0:
            h += 360

        # Saturation
        s = 0.0 if max_c == 0 else (delta / max_c) * 100

        # Value
        v = max_c * 100

        return (round(h), round(s, 1), round(v, 1))

    def _hue_name(self, h: int, s: float, v: float) -> str:
        """
        HSV → 可读颜色名

        饱和度 < 15% 或亮度 < 18% 时不做色相判断，直接归入灰阶。
        """
        # === 无彩色系 ===
        # 极暗
        if v < 10:
            return "纯黑"
        if v < 18:
            return "暗灰色" if s >= 15 else "纯黑"

        # 极亮
        if v > 95:
            return "纯白"

        # 低饱和度 → 灰阶
        if s < 15:
            if v < 30:
                return "深灰"
            elif v < 55:
                return "灰色"
            elif v < 80:
                return "浅灰"
            else:
                return "亮灰"

        # === 有彩色系 ===
        hue_name = "未知"
        for (lo, hi), name in self.HUE_RANGES:
            if lo <= h < hi:
                hue_name = name
                break
        if hue_name == "未知" and h >= 345:
            hue_name = "红"

        # 深色下降低饱和度修饰的权重（因为深色天然饱和度低）
        if v < 35:
            # 深色：前缀用"深"即可，不加"灰调"
            return f"深{hue_name}"
        elif v < 50:
            if s < 30:
                return f"暗{hue_name}"
            else:
                return f"深{hue_name}"
        elif v > 85:
            if s > 70:
                return f"亮{hue_name}"
            else:
                return f"浅{hue_name}"
        else:
            # 正常亮度
            if s < 25:
                return f"灰调{hue_name}"
            elif s < 50:
                return f"柔和{hue_name}"
            elif s > 80:
                return f"鲜艳{hue_name}"
            else:
                return hue_name

    def _rgb_to_hex(self, rgb: np.ndarray) -> str:
        r, g, b = [int(max(0, min(255, c))) for c in rgb]
        return f"#{r:02X}{g:02X}{b:02X}".upper()

    def _preprocess(self, image: np.ndarray,
                    mask: np.ndarray | None = None) -> tuple:
        """光照补偿 + mask"""
        if image is None or image.size == 0:
            return image, None

        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        lab = cv2.merge([l, a, b])
        image = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        if mask is None:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            _, mask_dark = cv2.threshold(gray, 20, 255, cv2.THRESH_BINARY)
            _, mask_light = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
            mask = cv2.bitwise_and(mask_dark, mask_light)

        return image, mask

    def extract_colors(self, image: np.ndarray,
                       mask: np.ndarray | None = None) -> list[dict]:
        """
        提取主色辅色

        Returns:
            [{"hex": "#XXXXXX", "name": "深蓝色", "ratio": 0.53}, ...]
        """
        if image is None or image.size == 0:
            return [{"hex": "#808080", "name": "灰色", "ratio": 1.0}]

        h_img, w_img = image.shape[:2]

        if mask is not None and mask.shape != (h_img, w_img):
            mask = cv2.resize(mask.astype(np.uint8), (w_img, h_img),
                              interpolation=cv2.INTER_NEAREST)

        image, auto_mask = self._preprocess(image, mask)
        effective_mask = mask if mask is not None else auto_mask
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        if effective_mask is not None:
            if effective_mask.dtype != bool:
                effective_mask = effective_mask > 0
            pixels = img_rgb[effective_mask].reshape(-1, 3)
        else:
            pixels = img_rgb.reshape(-1, 3)

        if len(pixels) < 50:
            return [{"hex": "#808080", "name": "灰色", "ratio": 1.0}]

        k = min(self.n_colors, max(2, len(pixels) // 200))
        kmeans = KMeans(n_clusters=k, n_init=10, random_state=42)
        labels = kmeans.fit_predict(pixels)
        total = len(labels)

        colors = []
        for i in range(k):
            ratio = np.sum(labels == i) / total
            if ratio < self.min_ratio:
                continue
            center_rgb = kmeans.cluster_centers_[i]
            # 过滤极暗/极亮噪音（占位色不算是有效衣物颜色）
            if np.mean(center_rgb) < 15 or np.mean(center_rgb) > 240:
                if ratio < 0.15:
                    continue
            hex_str = self._rgb_to_hex(center_rgb)
            r, g, b = int(center_rgb[0]), int(center_rgb[1]), int(center_rgb[2])
            h, s, v = self._rgb_to_hsv(r, g, b)
            name = self._hue_name(h, s, v)
            colors.append({
                "hex": hex_str,
                "name": name,
                "ratio": round(ratio, 3),
                "hsv": (h, s, v),
            })

        colors.sort(key=lambda x: x["ratio"], reverse=True)

        # 合并相近色（HSV 欧氏距离 < 20 且 色相接近）
        merged = []
        for c in colors:
            is_similar = False
            for m in merged:
                h1, s1, v1 = c["hsv"]
                h2, s2, v2 = m["hsv"]
                # 色相差（考虑环形）
                hue_diff = min(abs(h1 - h2), 360 - abs(h1 - h2))
                sv_diff = np.sqrt((s1 - s2) ** 2 + (v1 - v2) ** 2)
                if hue_diff < 25 and sv_diff < 20 and min(c["ratio"], m["ratio"]) > 0.03:
                    # 合并
                    total_r = m["ratio"] + c["ratio"]
                    m["ratio"] = round(total_r, 3)
                    is_similar = True
                    break
            if not is_similar:
                merged.append(c)

        total_ratio = sum(m["ratio"] for m in merged)
        for m in merged:
            m["ratio"] = round(m["ratio"] / total_ratio, 3)

        # 移除内部用的 hsv 字段
        for m in merged:
            m.pop("hsv", None)

        return merged[:3]
