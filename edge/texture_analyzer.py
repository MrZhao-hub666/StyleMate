"""
纹理与图案分析模块

基于 Gabor 滤波器 + GLCM + 频谱分析的纯传统视觉方法：
- 图案识别：纯色/条纹/格子/印花/迷彩/渐变
- 材质推测：纹理粗糙度 + 光泽度
"""

import cv2
import numpy as np
from skimage.feature import graycomatrix, graycoprops


class TextureAnalyzer:
    """衣物纹理 / 图案 / 材质分析器"""

    # Gabor 滤波器参数
    GABOR_KERNEL_SIZE = 21
    GABOR_SIGMA = 3.0
    GABOR_THETA = [0, np.pi/4, np.pi/2, 3*np.pi/4]  # 0°, 45°, 90°, 135°
    GABOR_LAMBDA = 8.0
    GABOR_GAMMA = 0.5

    def __init__(self):
        self.gabor_kernels = self._build_gabor_kernels()

    def _build_gabor_kernels(self) -> list:
        """预计算 Gabor 滤波器核"""
        kernels = []
        for theta in self.GABOR_THETA:
            kernel = cv2.getGaborKernel(
                (self.GABOR_KERNEL_SIZE, self.GABOR_KERNEL_SIZE),
                self.GABOR_SIGMA, theta,
                self.GABOR_LAMBDA, self.GABOR_GAMMA,
                0, ktype=cv2.CV_32F
            )
            kernels.append(kernel)
        return kernels

    def _compute_gabor_features(self, gray: np.ndarray) -> dict:
        """
        计算 Gabor 响应特征

        Returns:
            dict: {"mean_0": ..., "std_0": ..., "max_response": ..., "dominant_angle": ...}
        """
        responses = []
        for i, kernel in enumerate(self.gabor_kernels):
            filtered = cv2.filter2D(gray, cv2.CV_32F, kernel)
            responses.append({
                "angle_idx": i,
                "mean": float(np.mean(np.abs(filtered))),
                "std": float(np.std(np.abs(filtered))),
            })

        max_resp = max(responses, key=lambda x: x["mean"])
        all_means = [r["mean"] for r in responses]

        return {
            "mean_responses": all_means,
            "max_response": max_resp["mean"],
            "min_response": min(all_means),
            "response_variance": float(np.var(all_means)),
            # 方向性指标：最大值与最小值的比值
            "directionality": max_resp["mean"] / (min(all_means) + 1e-6),
            "dominant_angle": max_resp["angle_idx"],
        }

    def _compute_glcm_features(self, gray: np.ndarray) -> dict:
        """
        计算 GLCM 纹理统计特征

        Returns:
            dict: contrast, dissimilarity, homogeneity, energy, correlation, ASM
        """
        # 量化到 32 级灰度
        gray_q = (gray // 8).astype(np.uint8)

        # 4个方向的 GLCM（取平均）
        distances = [1, 2]
        angles = [0, np.pi/4, np.pi/2, 3*np.pi/4]

        glcm = graycomatrix(gray_q, distances=distances, angles=angles,
                            levels=32, symmetric=True, normed=True)

        contrast = graycoprops(glcm, "contrast").mean()
        dissimilarity = graycoprops(glcm, "dissimilarity").mean()
        homogeneity = graycoprops(glcm, "homogeneity").mean()
        energy = graycoprops(glcm, "energy").mean()
        correlation = graycoprops(glcm, "correlation").mean()
        asm = graycoprops(glcm, "ASM").mean()

        return {
            "contrast": float(contrast),
            "dissimilarity": float(dissimilarity),
            "homogeneity": float(homogeneity),
            "energy": float(energy),
            "correlation": float(correlation),
            "asm": float(asm),
        }

    def _compute_spectrum_features(self, gray: np.ndarray) -> dict:
        """
        频谱分析（FFT），检测周期性图案（如格子、条纹）
        """
        f = np.fft.fft2(gray.astype(float))
        fshift = np.fft.fftshift(f)
        magnitude = np.abs(fshift)

        h, w = magnitude.shape
        center_y, center_x = h // 2, w // 2

        # 排除直流分量周围
        mask_dc = np.ones((h, w), dtype=bool)
        mask_dc[center_y-5:center_y+5, center_x-5:center_x+5] = False

        # 峰值检测（周期性图案在频谱上表现为亮点）
        spectral_values = magnitude[mask_dc]
        mean_spec = float(np.mean(spectral_values))
        max_spec = float(np.max(spectral_values))
        std_spec = float(np.std(spectral_values))

        # 峰值数量（> mean + 2*std 视为显著峰值）
        n_peaks = int(np.sum(spectral_values > mean_spec + 2 * std_spec))

        # 周期性强度：最大峰值 / 均值
        periodicity = max_spec / (mean_spec + 1e-6)

        return {
            "mean_magnitude": mean_spec,
            "max_magnitude": max_spec,
            "std_magnitude": std_spec,
            "n_peaks": n_peaks,
            "periodicity": round(periodicity, 3),
        }

    def _compute_glossiness(self, image_bgr: np.ndarray) -> float:
        """
        光泽度分析（亮度分布的高偏度 → 高光泽，如丝绸、皮革）
        """
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = hist.flatten() / hist.sum()

        # 偏度 (skewness)
        values = np.arange(256)
        mean = np.sum(values * hist)
        std = np.sqrt(np.sum((values - mean) ** 2 * hist))
        if std < 1e-6:
            return 0.0
        skewness = np.sum((values - mean) ** 3 * hist) / (std ** 3)

        # 高亮度像素占比（>200）
        highlight_ratio = float(np.sum(hist[200:]))

        # 光泽度 = 偏度 * 0.6 + 高亮占比 * 0.4
        return round(float(skewness * 0.6 + highlight_ratio * 10 * 0.4), 3)

    def _check_gradient(self, image_bgr: np.ndarray) -> float:
        """
        检查是否有真正的渐变色
        通过纵向扫描亮度变化率来判断（渐变的亮度是连续单调变化的）
        Returns: gradient_score（0=纯色，1=明显渐变）
        """
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        # 每行的平均亮度
        row_means = np.mean(gray, axis=1)
        # 计算行间亮度变化的标准差（渐变应该是平滑单调的）
        diffs = np.diff(row_means)
        # 检查是否单调变化（所有差分同号）
        if len(diffs) < 5:
            return 0.0
        pos_count = np.sum(diffs > 0)
        neg_count = np.sum(diffs < 0)
        monotonicity = abs(pos_count - neg_count) / len(diffs)  # 越接近1越单调
        # 变化幅度
        total_change = abs(row_means[-1] - row_means[0]) / (np.mean(row_means) + 1)
        gradient_score = monotonicity * min(1.0, total_change * 3)
        return float(gradient_score)

    def identify_pattern(self, image_bgr: np.ndarray) -> dict:
        """
        识别图案类型

        决策逻辑（基于多特征融合，优先级从高到低）：
        - 纯色：GLCM 能量高 + Gabor 方差低
        - 条纹：Gabor 方向性强 + 频谱峰值多
        - 格子：频谱双方向峰值 + 强周期性
        - 渐变：纵向亮度单调变化
        - 印花/碎花：中等纹理复杂度
        - 默认归为纯色（最常见情况）
        """
        if image_bgr is None or image_bgr.size == 0:
            return {"pattern": "未知", "confidence": 0.0}

        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

        gabor_feat = self._compute_gabor_features(gray)
        glcm_feat = self._compute_glcm_features(gray)
        spec_feat = self._compute_spectrum_features(gray)
        gradient_score = self._check_gradient(image_bgr)

        energy = glcm_feat["energy"]
        contrast = glcm_feat["contrast"]
        directionality = gabor_feat["directionality"]
        periodicity = spec_feat["periodicity"]
        n_peaks = spec_feat["n_peaks"]
        variance = gabor_feat["response_variance"]

        # 条纹（方向性最强）
        if directionality > 3.0 and n_peaks > 6:
            confidence = min(1.0, directionality / 5.0)
            return {"pattern": "条纹", "confidence": round(confidence, 3)}

        # 格子（双方向峰值 + 强周期性）
        if 2.0 < directionality < 3.5 and periodicity > 3.0 and n_peaks > 8:
            return {"pattern": "格子", "confidence": round(min(0.9, periodicity / 5.0), 3)}

        # 渐变（纵向亮度单调变化）
        if gradient_score > 0.5:
            return {"pattern": "渐变", "confidence": round(gradient_score, 3)}

        # 纯色（高能量 + 低方差）
        if energy > 0.18 or variance < 80:
            confidence = min(1.0, max(energy / 0.3, (1 - variance / 200)))
            return {"pattern": "纯色", "confidence": round(confidence, 3)}

        # 碎花/印花（中等复杂度）
        if 0.06 < energy < 0.25 and contrast > 20:
            return {"pattern": "印花/碎花", "confidence": round(0.65, 3)}

        # 迷彩
        if variance > 120 and directionality < 2.0:
            return {"pattern": "迷彩/不规则纹理", "confidence": round(0.6, 3)}

        # 默认纯色（而非"规则纹理"）
        return {"pattern": "纯色", "confidence": 0.55}

    def estimate_fabric(self, image_bgr: np.ndarray, pattern: str) -> dict:
        """
        推测材质

        基于纹理粗糙度（GLCM contrast）+ 光泽度综合推断：
        """
        if image_bgr is None or image_bgr.size == 0:
            return {"fabric": "未知", "confidence": 0.0}

        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        glcm_feat = self._compute_glcm_features(gray)
        glossiness = self._compute_glossiness(image_bgr)

        contrast = glcm_feat["contrast"]
        homogeneity = glcm_feat["homogeneity"]

        # 粗糙度指标
        roughness = contrast / (homogeneity + 1e-6)

        # 决策逻辑
        if pattern == "纯色":
            if glossiness > 3.0:
                return {"fabric": "丝绸/缎面", "confidence": 0.8}
            elif roughness < 30:
                return {"fabric": "棉质", "confidence": 0.7}
            elif glossiness > 2.0:
                return {"fabric": "皮质/仿皮", "confidence": 0.65}
            else:
                return {"fabric": "棉/麻混纺", "confidence": 0.6}

        if pattern == "格子" or pattern == "条纹":
            if glossiness > 2.0:
                return {"fabric": "丝绸", "confidence": 0.6}
            else:
                return {"fabric": "棉质", "confidence": 0.7}

        if roughness > 200:
            return {"fabric": "牛仔/粗棉", "confidence": 0.7}

        if glossiness > 4.0:
            return {"fabric": "皮革", "confidence": 0.8}

        if homogeneity > 0.5 and roughness < 50:
            return {"fabric": "针织/毛衣", "confidence": 0.65}

        return {"fabric": "化纤混纺", "confidence": 0.5}

    def analyze(self, image_bgr: np.ndarray) -> dict:
        """
        一站式纹理分析

        Returns:
            {
                "pattern": 图案类型,
                "pattern_confidence": 置信度,
                "fabric": 推测材质,
                "fabric_confidence": 材质置信度,
                "glossiness": 光泽度,
            }
        """
        pattern_result = self.identify_pattern(image_bgr)
        fabric_result = self.estimate_fabric(image_bgr, pattern_result["pattern"])

        return {
            "pattern": pattern_result["pattern"],
            "pattern_confidence": pattern_result["confidence"],
            "fabric": fabric_result["fabric"],
            "fabric_confidence": fabric_result["confidence"],
            "glossiness": fabric_result.get("glossiness", self._compute_glossiness(image_bgr)),
        }


if __name__ == "__main__":
    analyzer = TextureAnalyzer()

    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    if ret:
        result = analyzer.analyze(frame)
        print(f"图案: {result['pattern']} (置信度: {result['pattern_confidence']})")
        print(f"材质: {result['fabric']} (置信度: {result['fabric_confidence']})")
        print(f"光泽度: {result['glossiness']}")
    cap.release()
