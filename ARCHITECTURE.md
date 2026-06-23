# StyleMate 架构文档

## 项目概述

AI 穿搭助手，三端协作：前端 Vue3、后端 FastAPI、边端 YOLO。

| 端 | 端口 | 技术 |
|---|------|------|
| 前端 | 5173 | Vue3 + Vite + Element Plus + Pinia |
| 后端 | 9000 | FastAPI + SQLAlchemy(async) + LangChain |
| 边端 | 9001 | FastAPI + YOLO(ultralytics) + OpenCV |

---

## 模型分工

| 模型 | 配置变量 | 调用位置 |
|------|---------|---------|
| **DeepSeek `deepseek-v4-flash`** | `DEEPSEEK_MODEL` | 搭配推荐、写真 prompt 优化 |
| **qwen3-vl-flash** | `DASHSCOPE_VISION_MODEL` | 穿搭评价、云端视觉精细识别 |
| **万相 2.7 `wan2.7-image`** | `DASHSCOPE_IMAGE_MODEL` | 创意写真图像生成 |
| **万相 2.7 `wan2.7-image-pro`** | `DASHSCOPE_IMAGE_MODEL_PRO` | 搭配推荐预览图生成 |
| **sentence-transformers** | 本地模型 | 知识库向量检索 |

---

## 一、个人相册

```
前端拍照/上传
     │
     ▼
POST /api/profile/gallery/upload
     │
     ├── 保存文件到磁盘 → GalleryImage 入库
     │
     └── 后台任务 _run_gallery_analysis
              │
              ├── 1) 发图片到边端 POST :9001/analyze (zone=portrait)
              │       边端: YOLO人体检测 → 颜色/图案/品类 → 人脸裁剪
              │
              └── 2) 写入 GalleryImageAnalysis
                       (has_person / clothing_colors / categories / pattern / face_crop_base64)
```

**触发风格画像重建**：每次分析完成后调用 `rebuild_style_profile()`。

---

## 二、个人衣橱

```
前端拍照/上传
     │
     ▼
POST /api/edge/upload/quick → Clothing 入库 (needs_cloud=True, 属性待补充)
     │
     ▼
前端调用边端分析 POST :9001/analyze (zone=single_garment)
     │        YOLO → 颜色/图案/面料/长度
     ▼
PUT /api/edge/upload/{id} → 更新 YOLO 属性到 Clothing
     │
     └── 后台任务 _run_cloud_vision
              │
              ├── 1) 传入 YOLO 文本属性 + 衣物裁剪原图
              │
              ├── 2) qwen3.7-plus 看图校验
              │        以 YOLO 为参考，视觉验证后返回：
              │        subcategory / primary_color / pattern / fabric
              │        / length_category / fit / neckline / sleeve
              │
              └── 3) Qwen 结果覆盖 YOLO，更新 Clothing 全部字段
                       needs_cloud 置为 False
```

**触发风格画像重建**：每次 `update_attributes` 和 `delete_clothing` 后。

---

## 三、风格画像

```
数据库数据源:
  ├── GalleryImageAnalysis (相册分析: 颜色/图案/品类 + 时间戳)
  └── Clothing (衣橱: 颜色/图案/品类/面料 + 创建时间)
         │
         ▼
  build_style_profile()
         │
         ├── 时间衰减权重: ≤7天1.0 / 8-30天0.8 / 31-90天0.5 / 91-365天0.3 / >365天0.15
         ├── 颜色归并: 深蓝→蓝色系, 暗红→红色系...
         │
         ▼
  UserStyleProfile:
    ├── color_preferences     [{color:"黑色", ratio:0.35}, ...]
    ├── pattern_preferences   {纯色:0.65, 条纹:0.15, ...}
    ├── category_preferences  {上装:0.40, 下装:0.30, ...}
    ├── style_tendency        "简约都市风" / "温暖休闲风" / ...
    └── dominant_colors_hex   ["#1a1a2e", "#2d4a7a", ...]
         │
         ▼
  format_style_for_llm() → 自然语言, 注入搭配推荐/写真/评价的 prompt
```

---

## 四、搭配推荐

```
前端选择场合/偏好/城市 + 上传本人照片
     │
     ▼
POST /api/recommend
     │
     ├── 查衣橱 Clothing 表 → [{id, zone, category, color, pattern, fabric, ...}]
     ├── 查风格画像 → style_prompt 文本
     │
     ▼
Phase 1: DeepSeek 文字方案 (2-3s)
     ├── 并行: 天气服务 + 知识库检索
     ├── 构建 prompt → DeepSeek → 3 套方案 JSON
     │
     ▼
Phase 2: 预览图生成 (30-60s, 条件满足时)
     ├── 人物照片? → 用户上传 | 相册含人原图
     ├── 衣橱有物品? → 至少一件
     └── 条件不满足 → need_confirm=true, 前端弹窗提示
     │
     ├── _pick_best_plan() → 选含衣橱物品最多的方案
     ├── _build_clothing_prompt() → "深蓝纯色棉T恤 + 黑色直筒牛仔裤..."
     └── 万相2.7-pro 图生图: 用户照片 + 穿搭描述 → preview_url

返回: {weather, recommendations: [{name, items, reason}], preview_url}
```

> 磁盘清理：`/generated/` 下超过 1 小时的文件会被定时清理；写真保存到相册后原 generated 图自动删除。

---

## 五、创意写真生成

```
前端输入描述 + 风格提示 (+ 可选上传照片)
     │
     ▼
POST /api/portrait/generate
     │
     ├── 0) 读取用户性别 (UserProfile.gender)
     ├── 1) 读取风格画像 → style_prompt
     ├── 2) 照片来源:
     │       ├── 用户上传了 → 直接用
     │       └── 未上传 → 从相册取最新含人原图 (_pick_best_face)
     │       └── 都没有 → HTTP 400
     │
     ├── 3) prompt 优化: portrait_agent.optimize_prompt()
     │       知识库检索风格趋势 → DeepSeek 优化为生图 prompt
     │       注入性别信息、风格偏好
     │
     ├── 4) 生图: image_gen.image_to_image()
     │       DashScope 万相 2.7 图生图 (wan2.7-image)
     │       图片 + 优化 prompt → 返回生成图 URL
     │
     └── 5) 保存到磁盘 /uploads/generated/
返回: {images: [url], optimized_prompt}
     │
     ▼
前端点"保存到相册" → POST /api/portrait/save
     ├── 复制到 /uploads/gallery/
     ├── 创建 GalleryImage 记录
     └── 后台触发相册分析 (同流程一)
```

---

## 六、穿搭评价

```
前端拍照/上传穿搭照片
     │
     ▼
POST /api/review
     │
     ├── 提取 crop_base64 (从 outfit_items[0])
     ├── 查风格画像 → style_prompt
     │
     ├── 并行: 边端 YOLO 分析
     │        POST :9001/analyze (zone=outfit)
     │        → 返回颜色/图案/面料/品类
     │
     └── qwen3.7-plus 多模态评价
              │
              ├── 输入: 原始穿搭照片 + YOLO属性(仅供参考) + 场合 + 风格画像
              ├── 提示词: "以照片视觉分析为主，边端数据仅辅助"
              │
              ▼
返回: {score, summary, highlights, weaknesses, suggestions, style_match}
```

---

## 七、边端分析服务

```
POST :9001/analyze
     │
     ├── Step 1: base64 解码 → cv2.imdecode
     │
     ├── Step 2: YOLO 人体检测 + 衣物区域提取
     │        detector.extract_clothing_crops()
     │        → [{crop, zone, bbox, has_person, mask}]
     │
     ├── Step 3: 七维属性分析 (attribute_pipeline)
     │        ├── 品类: ZONE_TO_CATEGORY 启发式映射
     │        ├── 颜色: K-means 聚类 + HSV 自动命名
     │        ├── 图案: Gabor + GLCM + 频谱分析
     │        ├── 面料: 纹理粗糙度 + 光泽度
     │        ├── 长度: 宽高比估算
     │        └── 裁剪图: cv2.imencode → base64
     │
     ├── Step 4: 人脸提取 (有人物时)
     │        body_h * 0.28 估算人脸区域 → 裁剪
     │
     └── Step 5: 返回 AnalyzeResponse
          {category, primary_color_name/hex, pattern, fabric, length_category, face_crop_base64, ...}
```

---

## 八、云端视觉精细识别

```
衣橱物件的 _run_cloud_vision 后台任务触发:

    YOLO属性 (参考)  +  衣物裁剪原图
         │                  │
         └──────┬───────────┘
                ▼
         qwen3.7-plus 看图校验
         │
         ├── 系统提示: 以你看到的图片为准，YOLO数据如有偏差请修正
         ├── 用户提示: YOLO属性(仅供参考) + 请分析全部属性
         │
         ▼
返回 11 个字段:
  subcategory / primary_color_name / primary_color_hex
  / secondary_color_name / secondary_color_hex
  / pattern / fabric / length_category
  / fit / neckline / sleeve
         │
         ▼
Qwen 结果覆盖 YOLO → 更新 Clothing 全部字段 → needs_cloud=False
```

---

## 数据流总览（本地开发）

```
┌──────────┐     HTTP(:9000)     ┌──────────┐     HTTP(:9001)    ┌──────────┐
│  前端     │ ←────────────────→ │  后端     │ ←───────────────→ │  边端     │
│  Vue3    │                    │  FastAPI  │                    │  YOLO    │
└──────────┘                    └──────────┘                    └──────────┘
     │                               │                               │
     │  拍照/上传                     │  照片 → 边端分析               │ YOLO人体检测
     │  API 请求                      │  属性 → DB 存储               │ 颜色K-means
     │  展示结果                      │  风格画像构建                  │ 图案Gabor
     │                               │  LLM 推理                     │ 面料分析
     │                               │                               │
     │                    ┌──────────┴──────────┐                   │
     │                    │   大模型调用          │                   │
     │                    │                     │                   │
     │                    │ DeepSeek ─ 搭配推荐  │                   │
     │                    │ DeepSeek ─ 写真优化  │                   │
     │                    │ qwen3-vl ─ 穿搭评价  │                   │
     │                    │ qwen3-vl ─ 视觉识别  │                   │
     │                    │ 万相2.7  ─ 图像生成  │                   │
     │                    └─────────────────────┘                   │
     │                                                              │
     └──────────── 用户交互层 ───────────────────────────────────────┘
```

## 云部署架构

云端（后端+前端）通过 `docker-compose.cloud.yml` 部署在服务器上，不引入 YOLO/OpenCV 等视觉依赖。边端通过 `docker-compose.edge.yml` 或 bat 脚本在本机启动，调用由浏览器端完成，无需服务器访问本机局域网。

```
┌── 你的云服务器 ──┐          ┌── 用户本机 ──┐
│                           │          │               │
│ 前端 Nginx (:80)          │  HTTP    │  浏览器       │
│  ↓ proxy /api             │←────────→│  ↓            │
│ 后端 FastAPI (:9000)      │          │  边端 YOLO    │
│  ↓ DeepSeek/Qwen/万相     │          │  (:9001)      │
│                           │          │               │
└───────────────────────────┘          └───────────────┘

关键改动：评价/分析时，前端先调本机边端 → 带结果发给后端，避免跨网络调用。
```

## 部署命令

云端和边端分离部署：

```bash
# 服务器上 — 仅启动云端（后端 + 前端），不引入 YOLO/OpenCV 依赖
cd /opt/StyleMate
docker compose -f docker-compose.cloud.yml up -d

# 用户本机 — 启动边端 YOLO（三种方式任选）
双击 start-edge.bat
# 或
cd edge && uv run uvicorn server:app --host 0.0.0.0 --port 9001
# 或 (Docker)
docker compose -f docker-compose.edge.yml up -d
```
