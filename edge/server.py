"""
StyleMate 边端分析 HTTP 服务

启动： uv run uvicorn server:app --host 0.0.0.0 --port 9001
API：  POST /analyze — 接收 base64 图片 → YOLO 分析 → 返回属性 JSON
"""

import base64
import time
import cv2
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from attribute_pipeline import AttributePipeline

app = FastAPI(title="StyleMate Edge Analyzer", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

pipeline = AttributePipeline(device="cpu")


class AnalyzeRequest(BaseModel):
    image_base64: str
    zone: str = "single_garment"


class AnalyzeResponse(BaseModel):
    category: str
    primary_color_hex: str
    primary_color_name: str
    primary_color_ratio: float
    secondary_color_hex: str | None = None
    secondary_color_name: str | None = None
    secondary_color_ratio: float = 0.0
    pattern: str = "未知"
    pattern_confidence: float = 0.0
    fabric: str = "未知"
    fabric_confidence: float = 0.0
    length_category: str = "未知"
    has_person: bool = False
    face_crop_base64: str | None = None  # 有人物时返回人脸裁剪


def _log(step: str, msg: str):
    """统一日志格式"""
    print(f"[edge] [{step}] {msg}", flush=True)


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    t0 = time.time()

    # ===== Step 1: 解码 base64 =====
    b64 = req.image_base64.split(",")[-1] if "," in req.image_base64 else req.image_base64
    _log("1/4 解码", f"base64 长度={len(b64)} 字符, zone={req.zone}")

    try:
        img_bytes = base64.b64decode(b64)
    except Exception as e:
        _log("1/4 解码", f"❌ base64 解析失败: {e}")
        return AnalyzeResponse(category="衣物", primary_color_hex="#808080", primary_color_name="未知", primary_color_ratio=1.0)

    nparr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        _log("1/4 解码", f"❌ cv2.imdecode 失败 (bytes={len(img_bytes)})")
        return AnalyzeResponse(category="衣物", primary_color_hex="#808080", primary_color_name="未知", primary_color_ratio=1.0)

    _log("1/4 解码", f"✅ 尺寸={frame.shape[1]}x{frame.shape[0]}")

    # ===== Step 2: YOLO 人体检测 + 区域提取 =====
    _log("2/4 YOLO检测", "运行中...")
    t1 = time.time()
    try:
        crops = pipeline.detector.extract_clothing_crops(frame)
    except Exception as e:
        _log("2/4 YOLO检测", f"❌ 失败: {e}")
        return AnalyzeResponse(category="衣物", primary_color_hex="#808080", primary_color_name="未知", primary_color_ratio=1.0)
    _log("2/4 YOLO检测", f"✅ 检测到 {len(crops)} 个区域, 耗时={(time.time()-t1)*1000:.0f}ms")

    # ===== Step 3: 七维属性分析 =====
    _log("3/4 属性分析", "运行中...")
    t2 = time.time()
    try:
        if req.zone == "single_garment":
            attr = pipeline.process_single_garment(frame)
        elif crops:
            attr = pipeline.analyze_region(
                crops[0]["crop"], crops[0]["zone"],
                has_person=crops[0].get("has_person", False),
                mask=crops[0].get("mask"),
            )
        else:
            attr = pipeline.process_single_garment(frame)
    except Exception as e:
        _log("3/4 属性分析", f"❌ 失败: {e}")
        return AnalyzeResponse(category="衣物", primary_color_hex="#808080", primary_color_name="未知", primary_color_ratio=1.0)

    elapsed = (time.time() - t0) * 1000
    _log("3/4 属性分析", f"✅ 耗时={elapsed:.0f}ms")

    # ===== Step 4: 提取人脸裁剪 =====
    face_b64 = None
    if attr.has_person or req.zone in ("portrait", "outfit"):
        _log("4a 人脸提取", "运行中...")
        try:
            persons = pipeline.detector.detect_person_with_pose(frame)
            if persons:
                p = persons[0]
                x1, y1, x2, y2 = p["bbox"]
                body_h = y2 - y1
                face_y2 = min(y1 + int(body_h * 0.28), y2)
                face_crop = frame[y1:face_y2, x1:x2]
                if face_crop is not None and face_crop.size > 200 and face_crop.shape[0] > 20 and face_crop.shape[1] > 20:
                    _, buf = cv2.imencode(".jpg", face_crop, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    face_b64 = "data:image/jpeg;base64," + base64.b64encode(buf).decode()
                    _log("4a 人脸提取", f"✅ 提取成功 size={face_crop.shape[1]}x{face_crop.shape[0]}")
                else:
                    _log("4a 人脸提取", "⚠ 裁剪区域过小，跳过")
            else:
                _log("4a 人脸提取", "⚠ 未检测到人物")
        except Exception as e:
            _log("4a 人脸提取", f"❌ 失败: {e}")

    # ===== Step 5: 组装返回 =====
    _log("4/4 返回", f"品类={attr.category} | 主色={attr.primary_color_name}({attr.primary_color_hex}) | 图案={attr.pattern} | 面料={attr.fabric} | 有人脸={bool(face_b64)}")
    return AnalyzeResponse(
        category=attr.category,
        primary_color_hex=attr.primary_color_hex,
        primary_color_name=attr.primary_color_name,
        primary_color_ratio=attr.primary_color_ratio,
        secondary_color_hex=attr.secondary_color_hex,
        secondary_color_name=attr.secondary_color_name,
        secondary_color_ratio=attr.secondary_color_ratio,
        pattern=attr.pattern,
        pattern_confidence=attr.pattern_confidence,
        fabric=attr.fabric,
        fabric_confidence=attr.fabric_confidence,
        length_category=attr.length_category,
        has_person=attr.has_person,
        face_crop_base64=face_b64,
    )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "StyleMate Edge Analyzer"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9001)
