"""
AI 生图服务 — 阿里 DashScope 万相2.7 图生图
"""
import json
import httpx
import base64
import asyncio
from app.config import DASHSCOPE_API_KEY, DASHSCOPE_IMAGE_MODEL

DASHSCOPE_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc"
PFX = "[image_gen]"


async def image_to_image(
    image_base64: str,
    prompt: str,
    model: str = DASHSCOPE_IMAGE_MODEL,
    gender: str = "未设置",
) -> dict:
    """
    图生图（人物写真/风格迁移）— 使用万相2.7

    Args:
        image_base64: 用户照片 base64（直接传 base64 字符串或带 data: 前缀）
        prompt: 风格描述
        model: 模型名，默认 wan2.7-image（普通版，速度快）

    Returns:
        {"model": "...", "images": ["base64..."], "prompt": "..."}
    """
    if not DASHSCOPE_API_KEY:
        print(f"{PFX} ❌ DASHSCOPE_API_KEY 未配置", flush=True)
        return {"error": "未配置 DASHSCOPE_API_KEY", "model": model}

    # 压缩大图（超过1MB的图片缩放到1024宽，避免DashScope断连）
    MAX_SIZE = 800 * 1024  # 800KB
    b64 = image_base64.split(",")[-1] if "," in image_base64 else image_base64
    if len(b64) > MAX_SIZE:
        try:
            from PIL import Image
            import io
            img_data = base64.b64decode(b64)
            img = Image.open(io.BytesIO(img_data))
            w, h = img.size
            if max(w, h) > 1024:
                ratio = 1024 / max(w, h)
                img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=75)
            b64 = base64.b64encode(buf.getvalue()).decode()
            print(f"{PFX} 图片压缩: {w}x{h} → {img.size[0]}x{img.size[1]} ({len(img_data)}→{len(buf.getvalue())} bytes)", flush=True)
        except ImportError:
            pass  # PIL 不可用时跳过压缩

    img_b64 = f"data:image/jpeg;base64,{b64}"

    print(f"{PFX} 图生图: model={model} face_len={len(img_b64)} prompt={prompt[:60]}...", flush=True)

    # 万相2.7 多模态生成接口
    edits_url = f"{DASHSCOPE_URL}/multimodal-generation/generation"

    headers = {
        "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"image": img_b64},
                        {"text": (
                            f"请基于这张人物照片生成写真。要求：\n"
                            f"必须完全保留照片中人物的面部五官、脸型、肤色、发型和身份，不允许任何改变。\n"
                            f"仅更换人物的服装、姿势和背景场景为以下描述，人物外貌必须与原图完全一致。\n"
                            f"人物性别：{'男性' if gender in ('男','男性','male') else '女性' if gender in ('女','女性','female') else '未知，请根据参考照片判断'}。\n"
                            f"目标：{prompt}"
                        )},
                    ],
                }
            ],
        },
        "parameters": {
            "n": 1,
            "size": "2K",           # 图像编辑最高支持 2K
            "watermark": False,
            "thinking_mode": False,  # 有图片输入时不生效，显式关闭
        },
    }

    async with httpx.AsyncClient(timeout=180) as client:
        print(f"{PFX} 提交图生图任务 → {edits_url}", flush=True)
        resp = await client.post(
            edits_url,
            headers=headers,
            json=payload,
        )

        # 安全解析响应（404 等可能返回空 body）
        try:
            data = resp.json()
        except Exception:
            data = {"raw_status": resp.status_code, "raw_text": resp.text[:500]}

        print(f"{PFX} 提交响应 HTTP {resp.status_code} keys={list(data.keys())}", flush=True)

        if resp.status_code >= 400:
            err_info = data.get("message", "") or data.get("error", {}).get("message", "") or json.dumps(data, ensure_ascii=False)
            print(f"{PFX} ❌ 提交失败: {err_info[:500]}", flush=True)
            return {"error": f"提交生图任务失败: {err_info[:300]}", "model": model}

        # 万相2.7 多模态同步返回格式：
        # output.choices[0].message.content[0].image = OSS URL
        choices = data.get("output", {}).get("choices", [])
        if choices:
            images = []
            for choice in choices:
                content = choice.get("message", {}).get("content", [])
                for item in content:
                    if item.get("type") == "image" and item.get("image"):
                        url = item["image"]
                        img_resp = await client.get(url)
                        images.append(base64.b64encode(img_resp.content).decode())
            if images:
                print(f"{PFX} ✅ 图生图成功: {len(images)}张", flush=True)
                return {"model": model, "images": images, "prompt": prompt}

        # 兜底：异步格式 task_id
        task_id = data.get("output", {}).get("task_id")
        if task_id:
            print(f"{PFX} 异步任务ID={task_id}，开始轮询...", flush=True)
            poll_headers = {"Authorization": f"Bearer {DASHSCOPE_API_KEY}"}
            return await _poll_result(client, poll_headers, task_id, model, prompt)

        print(f"{PFX} ❌ 无法解析响应: {json.dumps(data, ensure_ascii=False)[:500]}", flush=True)
        return {"error": "图生图返回格式异常", "model": model, "detail": data}


async def _extract_images(client: httpx.AsyncClient, results: list) -> list:
    """从 results 中提取 base64 图片（url 需下载）"""
    images = []
    for r in results:
        if "url" in r:
            async with client.get(r["url"]) as img_resp:
                images.append(base64.b64encode(img_resp.content).decode())
        elif "b64_image" in r:
            images.append(r["b64_image"])
    return images


async def _poll_result(client: httpx.AsyncClient, headers: dict,
                       task_id: str, model: str, prompt: str,
                       max_retries: int = 30, interval: float = 1.0) -> dict:
    """轮询异步生图任务结果"""
    for i in range(max_retries):
        await asyncio.sleep(interval)
        resp = await client.get(
            f"{DASHSCOPE_URL}/image-generation/generation/{task_id}",
            headers=headers,
        )
        data = resp.json()
        status = data.get("output", {}).get("task_status")

        # 每5次打印一次进度
        if i % 5 == 0:
            print(f"{PFX} 轮询 [{i+1}/{max_retries}] 状态={status}", flush=True)

        if status == "SUCCEEDED":
            results = data.get("output", {}).get("results", [])
            images = await _extract_images(client, results)
            print(f"{PFX} ✅ 生图成功: {len(images)}张 共{sum(len(img) for img in images)}bytes", flush=True)
            return {"model": model, "images": images, "prompt": prompt}
        elif status in ("FAILED", "ERROR"):
            print(f"{PFX} ❌ 生图失败: {json.dumps(data, ensure_ascii=False)[:500]}", flush=True)
            return {"error": "生图失败", "detail": data}

    print(f"{PFX} ❌ 生图超时 task_id={task_id}", flush=True)
    return {"error": "生图超时", "task_id": task_id}
