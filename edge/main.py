"""
StyleMate 边端主入口

用法：
    python main.py                        # 摄像头模式
    python main.py a.jpg                  # 图片模式
    python main.py a.jpg -u               # 上传到云端
    python main.py a.jpg -u -s http://...  # 指定服务器
"""

import argparse
import cv2
import json
import time
from pathlib import Path
from attribute_pipeline import AttributePipeline
from uploader import CloudUploader


def print_sep(char="=", w=60):
    print(char * w)


def print_attr(attr, index: int = 1):
    """格式化输出 — 区分边端即时 vs 待云端补充"""
    zone_label = attr.zone
    if attr.zone == "shoes":
        zone_label = "👟 shoes"

    print(f"\n{'─' * 52}")
    print(f"  衣物 #{index}  [{zone_label}]  has_person={attr.has_person}")
    print(f"{'─' * 52}")

    # 边端即时（✓）
    print(f"  ✓ 品类大类: {attr.category}    (边端启发式)")
    print(f"  ✓ 主色    : {attr.primary_color_name}  {attr.primary_color_hex}  ({attr.primary_color_ratio*100:.0f}%)")
    if attr.secondary_color_name and attr.secondary_color_ratio > 0.05:
        print(f"  ✓ 辅色    : {attr.secondary_color_name}  {attr.secondary_color_hex}  ({attr.secondary_color_ratio*100:.0f}%)")
    print(f"  ✓ 图案    : {attr.pattern}  (置信度: {attr.pattern_confidence})")

    # 鞋履不显示领型/袖长
    if attr.zone != "shoes":
        print(f"  ✓ 材质    : {attr.fabric}  (光泽度: {attr.glossiness})")
        print(f"  ✓ 长度    : {attr.length_category}")
        print(f"  ⏳ 细分类  : {attr.subcategory}   → 待云端视觉识别")
        print(f"  ⏳ 领型    : {attr.neckline}       → 待云端视觉识别")
        print(f"  ⏳ 袖长    : {attr.sleeve}         → 待云端视觉识别")
        print(f"  ⏳ 版型    : {attr.fit}            → 待云端视觉识别")
    else:
        print(f"  ✓ 材质    : {attr.fabric}")
        print(f"  ⏳ 细分类  : {attr.subcategory}   → 待云端视觉识别")


def camera_mode(pipeline: AttributePipeline, uploader: CloudUploader = None):
    """摄像头实时模式"""
    print("正在打开摄像头...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ 无法打开摄像头！")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    print("\n📷 摄像头就绪 | [S]解析 [U]解析+上传 [Q]退出")
    print_sep()

    count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        cv2.putText(frame, "[S]can  [U]pload  [Q]uit", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow("StyleMate Edge", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            print("\n👋 退出")
            break

        elif key in (ord('s'), ord('u')):
            print(f"\n⏳ 解析中...")
            t0 = time.time()
            results = pipeline.process_frame(frame)
            elapsed = (time.time() - t0) * 1000

            print(f"✅ 解析完成 ({elapsed:.0f}ms)，检测到 {len(results)} 个区域：")
            for i, attr in enumerate(results):
                count += 1
                print_attr(attr, count)

            if key == ord('u') and uploader and results:
                print(f"\n📤 上传到 {uploader.base_url} ...")
                try:
                    if uploader.health_check():
                        resp = uploader.upload_batch(results)
                        print(f"✅ 上传成功: {json.dumps(resp, ensure_ascii=False, indent=2)[:400]}")
                    else:
                        print("❌ 云端不可达")
                except Exception as e:
                    print(f"❌ 上传失败: {e}")

    cap.release()
    cv2.destroyAllWindows()


def image_mode(pipeline: AttributePipeline, filepath: str, uploader: CloudUploader = None):
    """图片解析模式"""
    p = Path(filepath)
    if not p.exists():
        print(f"❌ 文件不存在: {filepath}")
        return

    print(f"⏳ 解析: {p.name} ...")
    t0 = time.time()

    try:
        results = pipeline.process_image_file(str(p))
        elapsed = (time.time() - t0) * 1000
        print(f"✅ 解析完成 ({elapsed:.0f}ms)，{len(results)} 个区域：")

        for i, attr in enumerate(results):
            print_attr(attr, i + 1)

        # 导出 JSON（不含 base64 图片，太大）
        json_path = p.with_suffix(".json")
        data = [asdict_custom(a) for a in results]
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n📄 已保存: {json_path}")

        if uploader and results:
            print(f"\n📤 上传到 {uploader.base_url} ...")
            try:
                if uploader.health_check():
                    resp = uploader.upload_batch(results)
                    print("✅ 上传成功")
                else:
                    print("❌ 云端不可达")
            except Exception as e:
                print(f"❌ 上传失败: {e}")

    except Exception as e:
        print(f"❌ 失败: {e}")


def asdict_custom(attr) -> dict:
    """导出时去掉 base64（太大），保留元数据"""
    from dataclasses import asdict
    d = asdict(attr)
    d.pop('crop_base64', None)
    return d


def main():
    parser = argparse.ArgumentParser(
        description="StyleMate Edge — YOLO 衣物属性解析引擎",
        epilog="用法: python main.py          # 摄像头\n"
               "     python main.py a.jpg     # 解析图片\n"
               "     python main.py a.jpg -u  # 解析并上传",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("image", nargs="?", type=str, default=None,
                        help="图片路径（可选，不传则打开摄像头）")
    parser.add_argument("-u", "--upload", action="store_true", help="上传到云端")
    parser.add_argument("-s", "--server", type=str, default="http://localhost:9000",
                        help="云端地址")
    parser.add_argument("-d", "--device", type=str, default="cpu", help="推理设备")
    args = parser.parse_args()

    print_sep("═")
    print("  🧥 StyleMate Edge — YOLO 衣物属性解析引擎")
    print_sep("═")
    print(f"  设备: {args.device}")
    print(f"  ✓ 边端即时: 区域检测 + 颜色 + 图案 + 材质 + 长度")

    pipeline = AttributePipeline(device=args.device)
    uploader = CloudUploader(base_url=args.server) if args.upload else None

    if args.upload:
        print(f"  ⏳ 待云端补充: 品类细分 + 领型 + 袖长 + 版型")
        print(f"  云端地址: {args.server}")
    print_sep("═")

    if args.image:
        image_mode(pipeline, args.image, uploader)
    else:
        camera_mode(pipeline, uploader)


if __name__ == "__main__":
    main()
