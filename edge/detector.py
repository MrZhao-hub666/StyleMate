"""
YOLOv8-seg 人体检测 + 衣物区域提取

功能：检测人体 → 分区(upper/lower/shoes/full) → 返回裁剪图+mask
"""

import cv2
import numpy as np
from ultralytics import YOLO


class ClothingDetector:
    """人体检测 + 衣物区域提取"""

    KP = {
        "left_shoulder": 5, "right_shoulder": 6,
        "left_elbow": 7, "right_elbow": 8,
        "left_wrist": 9, "right_wrist": 10,
        "left_hip": 11, "right_hip": 12,
        "left_knee": 13, "right_knee": 14,
        "left_ankle": 15, "right_ankle": 16,
    }

    def __init__(self, model_path: str = "yolov8n-seg.pt", device: str = "cpu",
                 conf_threshold: float = 0.5, kp_threshold: float = 0.15):
        self.model = YOLO(model_path)
        self.device = device
        self.conf_threshold = conf_threshold
        self.kp_threshold = kp_threshold

    def detect_person_with_pose(self, image: np.ndarray) -> list[dict]:
        """检测人体，返回bbox + keypoints + mask"""
        results = self.model(image, device=self.device, verbose=False, classes=[0])
        h, w = image.shape[:2]
        persons = []

        for r in results:
            if r.boxes is None:
                continue
            boxes = r.boxes.xyxy.cpu().numpy()
            confs = r.boxes.conf.cpu().numpy() if r.boxes.conf is not None else None
            keypoints_data = []
            if r.keypoints is not None and r.keypoints.data is not None:
                keypoints_data = r.keypoints.data.cpu().numpy()
            masks_data = None
            if r.masks is not None and r.masks.data is not None:
                masks_data = r.masks.data.cpu().numpy()

            for i, box in enumerate(boxes):
                conf = float(confs[i]) if confs is not None else 1.0
                if conf < self.conf_threshold:
                    continue
                person = {"bbox": tuple(map(int, box[:4])), "conf": conf,
                          "keypoints": [], "mask": None}
                if i < len(keypoints_data):
                    kp = keypoints_data[i]
                    person["keypoints"] = [
                        {"x": float(kp[j]), "y": float(kp[j+1]), "conf": float(kp[j+2])}
                        for j in range(0, len(kp), 3)
                    ]
                if masks_data is not None and i < len(masks_data):
                    raw_mask = masks_data[i]
                    if raw_mask.shape != (h, w):
                        raw_mask = cv2.resize(raw_mask.astype(np.float32), (w, h),
                                              interpolation=cv2.INTER_LINEAR)
                    person["mask"] = raw_mask > 0.5
                persons.append(person)
        return persons

    def _kp_valid(self, kp: dict) -> bool:
        return (kp.get("conf", 0) >= self.kp_threshold and kp["x"] > 0 and kp["y"] > 0)

    def _body_part_visible(self, keypoints: list[dict], indices: list[int]) -> bool:
        if len(keypoints) <= max(indices):
            return False
        return sum(1 for i in indices if self._kp_valid(keypoints[i])) >= 1

    def _crop_region(self, image: np.ndarray, bbox: tuple, keypoints: list[dict],
                     top_indices: list[int], bottom_indices: list[int],
                     pad: int = 15, fallback_pct: tuple = (0.0, 0.45)) -> np.ndarray:
        h, w = image.shape[:2]
        x1, y1, x2, y2 = bbox
        valid_tops = [keypoints[i]["y"] for i in top_indices
                      if i < len(keypoints) and self._kp_valid(keypoints[i])]
        valid_bottoms = [keypoints[i]["y"] for i in bottom_indices
                         if i < len(keypoints) and self._kp_valid(keypoints[i])]
        body_h = y2 - y1
        top = y1 if not valid_tops else max(y1, int(min(valid_tops) - body_h * 0.1))
        bottom = y2 if not valid_bottoms else min(y2, int(max(valid_bottoms) + body_h * 0.05))
        if not valid_tops and not valid_bottoms:
            top = int(y1 + body_h * fallback_pct[0])
            bottom = int(y1 + body_h * fallback_pct[1])
        top = max(0, top - pad)
        bottom = min(h, bottom + pad)
        x1_c = max(0, x1 - 20)
        x2_c = min(w, x2 + 20)
        return image[top:bottom, x1_c:x2_c] if top < bottom and x1_c < x2_c else None

    def _crop_upper(self, image: np.ndarray, bbox: tuple, keypoints: list[dict]) -> np.ndarray:
        if self._body_part_visible(keypoints, [self.KP["left_shoulder"], self.KP["right_shoulder"]]):
            return self._crop_region(image, bbox, keypoints,
                                     [self.KP["left_shoulder"], self.KP["right_shoulder"]],
                                     [self.KP["left_hip"], self.KP["right_hip"]])
        return self._crop_region(image, bbox, keypoints, [], [], fallback_pct=(0.0, 0.5))

    def _crop_lower(self, image: np.ndarray, bbox: tuple, keypoints: list[dict]) -> np.ndarray:
        if self._body_part_visible(keypoints, [self.KP["left_hip"], self.KP["right_hip"],
                                               self.KP["left_knee"], self.KP["right_knee"]]):
            return self._crop_region(image, bbox, keypoints,
                                     [self.KP["left_hip"], self.KP["right_hip"]],
                                     [self.KP["left_ankle"], self.KP["right_ankle"],
                                      self.KP["left_knee"], self.KP["right_knee"]])
        h, w = image.shape[:2]
        x1, y1, x2, y2 = bbox
        body_h = y2 - y1
        if body_h < 200:
            return None
        top = int(y1 + body_h * 0.45)
        bottom = y2
        x1_c = max(0, x1 - 20)
        x2_c = min(w, x2 + 20)
        lower = image[top:bottom, x1_c:x2_c]
        return lower if lower.size > 500 else None

    def _crop_shoes(self, image: np.ndarray, bbox: tuple, keypoints: list[dict]) -> np.ndarray:
        if self._body_part_visible(keypoints, [self.KP["left_ankle"], self.KP["right_ankle"]]):
            h, w = image.shape[:2]
            x1, y1, x2, y2 = bbox
            ankle_ys = [keypoints[idx]["y"]
                        for idx in [self.KP["left_ankle"], self.KP["right_ankle"]]
                        if idx < len(keypoints) and self._kp_valid(keypoints[idx])]
            if ankle_ys:
                shoe_top = int(min(ankle_ys))
                shoe_bottom = min(h, int(max(ankle_ys) + (y2 - max(ankle_ys)) * 1.5))
                x1_c = max(0, x1 - 30)
                x2_c = min(w, x2 + 30)
                shoe_img = image[shoe_top:shoe_bottom, x1_c:x2_c]
                if shoe_img is not None and shoe_img.shape[0] > 5:
                    return shoe_img
        h, w = image.shape[:2]
        x1, y1, x2, y2 = bbox
        body_h = y2 - y1
        if body_h < 300:
            return None
        shoe_top = int(y2 - body_h * 0.15)
        shoe_bottom = y2
        x1_c = max(0, x1 - 30)
        x2_c = min(w, x2 + 30)
        shoe_img = image[shoe_top:shoe_bottom, x1_c:x2_c]
        return shoe_img if shoe_img is not None and shoe_img.shape[0] > 15 and shoe_img.shape[1] > 15 else None

    def _crop_full(self, image: np.ndarray, bbox: tuple, keypoints: list[dict] = None) -> np.ndarray:
        h, w = image.shape[:2]
        x1, y1, x2, y2 = bbox
        x1, y1 = max(0, x1 - 20), max(0, y1 - 10)
        x2, y2 = min(w, x2 + 20), min(h, y2 + 10)
        return image[y1:y2, x1:x2] if y1 < y2 and x1 < x2 else None

    def _get_zone_mask(self, person_mask: np.ndarray, bbox: tuple,
                       keypoints: list[dict], zone: str) -> np.ndarray:
        if person_mask is None:
            return None
        x1, y1, x2, y2 = bbox
        h, w = person_mask.shape
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        zone_mask = person_mask.copy()
        if zone == "upper":
            for idx in [self.KP["left_hip"], self.KP["right_hip"]]:
                if idx < len(keypoints) and self._kp_valid(keypoints[idx]):
                    zone_mask[int(keypoints[idx]["y"]):] = False
                    break
        elif zone == "lower":
            for idx in [self.KP["left_hip"], self.KP["right_hip"]]:
                if idx < len(keypoints) and self._kp_valid(keypoints[idx]):
                    zone_mask[:int(keypoints[idx]["y"])] = False
                    break
        elif zone == "shoes":
            for idx in [self.KP["left_ankle"], self.KP["right_ankle"]]:
                if idx < len(keypoints) and self._kp_valid(keypoints[idx]):
                    zone_mask[:int(keypoints[idx]["y"])] = False
                    break
        return zone_mask[y1:y2, x1:x2]

    def extract_clothing_crops(self, image: np.ndarray) -> list[dict]:
        persons = self.detect_person_with_pose(image)
        if not persons:
            h, w = image.shape[:2]
            return [{"zone": "single_garment", "crop": image,
                     "bbox": (0, 0, w, h), "person_id": -1,
                     "has_person": False, "mask": None}]
        crops = []
        for pid, person in enumerate(persons):
            bbox = person["bbox"]
            kps = person["keypoints"]
            person_mask = person.get("mask")
            for crop_fn, zone_name in [
                (self._crop_upper, "upper"),
                (self._crop_lower, "lower"),
                (self._crop_shoes, "shoes"),
                (self._crop_full, "full"),
            ]:
                crop = crop_fn(image, bbox, kps)
                if crop is not None and crop.size > (100 if zone_name != "shoes" else 50):
                    crops.append({
                        "zone": zone_name, "crop": crop, "bbox": bbox,
                        "person_id": pid, "has_person": True,
                        "mask": self._get_zone_mask(person_mask, bbox, kps, zone_name),
                    })
        if not crops:
            h, w = image.shape[:2]
            return [{"zone": "single_garment", "crop": image,
                     "bbox": (0, 0, w, h), "person_id": -1,
                     "has_person": False, "mask": None}]
        return crops
