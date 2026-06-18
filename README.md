<p align="center">
  <h1 align="center">StyleMate</h1>
  <p align="center">您的专属 AI 穿搭顾问，拍照即分析，一键试穿预览</p>
</p>

<p align="center">
  <a href="#-功能一览"><strong>功能</strong></a> ·
  <a href="#-云端部署"><strong>部署</strong></a> ·
  <a href="#-技术架构"><strong>架构</strong></a> ·
  <a href="#-项目结构"><strong>目录</strong></a> ·
  <a href="#-截图"><strong>截图</strong></a>
</p>

---

## 🎯 功能一览

| 功能 | 说明 |
|------|------|
| 📸 **个人相册** | 上传照片 → 边端 YOLO 识别人脸和衣物，自动打标签 |
| 👗 **个人衣橱** | 拍照入库 → YOLO 分析颜色/图案/面料 → 大模型看图校验，精确到领型袖型 |
| 🧠 **风格画像** | 自动聚合历史数据，学习你的颜色偏好、穿搭风格，删数据自动清零 |
| ✨ **AI 搭配推荐** | 选场合 → DeepSeek 出 3 套方案 → 万相 2.7-Pro 生成上身试穿预览图，三联可下载 |
| 🎨 **创意写真** | 上传照片 + 描述 → AI 保留人脸，换装换场景，下载到本地 |
| 📝 **AI 穿搭评价** | 拍照当前穿搭 → YOLO 参考 + 视觉模型看图打分，亮点/不足/建议一目了然 |

---

## ☁️ 云端部署

### 前置条件

- 一台云服务器（2 核 4G 以上），已安装 Docker
- 本机启动边端 YOLO 服务（见下方）

### 1. 拉取代码

```bash
ssh root@你的服务器IP
cd /opt
git clone https://github.com/MrZhao-hub666/StyleMate.git
cd StyleMate
```

### 2. 配置密钥

```bash
cp backend/.env.example backend/.env
vim backend/.env
```

填入你的 API 密钥：

```env
DEEPSEEK_API_KEY=你的DeepSeek密钥
DASHSCOPE_API_KEY=你的阿里DashScope密钥
```

### 3. 启动

```bash
docker compose up -d
```

部署完成，浏览器访问 `http://你的服务器IP` 即可。

---

### 🖥 本机启动边端

边端 YOLO 分析服务需要在用户本机运行（需要摄像头 + 本地算力）：

```bash
cd edge
uv sync                    # 首次安装依赖（自动下载 YOLO 模型）
uv run uvicorn server:app --host 0.0.0.0 --port 9001
```

> 💡 YOLO 默认使用 ultralytics 预训练权重 + 几何估算。如需更高精度，可用自己的衣物标注数据微调后替换。

---

## 🏗 技术架构

```
┌── 云服务器 ──────────────┐          ┌── 用户本机 ──┐
│                          │          │               │
│ 前端 Nginx (:80)         │  HTTP    │  浏览器       │
│  ↓ reverse proxy         │←────────→│  ↓            │
│ 后端 FastAPI (:9000)     │          │  边端 YOLO    │
│  ↓ DeepSeek/Qwen/万相     │          │  (:9001)      │
│                          │          │               │
└──────────────────────────┘          └───────────────┘
```

| 大模型 | 服务商 | 用途 |
|--------|--------|------|
| DeepSeek `deepseek-v4-flash` | deepseek.com | 搭配推荐、写真 prompt 优化 |
| 通义千问 `qwen3-vl-flash` | 阿里 DashScope | 穿搭视觉评价、衣橱云端校验 |
| 万相 2.7-Pro | 阿里 DashScope | 上身试穿预览、创意写真生成 |

详细架构见 [ARCHITECTURE.md](ARCHITECTURE.md)。

---

## 📁 项目结构

```
StyleMate/
├── backend/                 # 云端后端 (FastAPI :9000)
│   ├── app/
│   │   ├── api/             # 接口层
│   │   ├── agent/           # LLM Agent
│   │   ├── services/        # 服务层 (生图/天气/风格画像/清理)
│   │   ├── models/          # SQLAlchemy 模型
│   │   ├── knowledge/       # 知识库 (ChromaDB)
│   │   └── config.py        # 统一配置入口
│   ├── .env.example         # 密钥模板
│   └── Dockerfile
│
├── edge/                    # 边端 YOLO (本机运行 :9001)
│   ├── server.py            # HTTP 分析服务
│   ├── detector.py          # YOLO 人体检测
│   ├── attribute_pipeline.py # 七维属性解析
│   ├── color_analyzer.py    # K-means 颜色提取
│   └── texture_analyzer.py  # 图案面料分析
│
├── frontend/                # 前端 (Vue3 + Vite)
│   ├── src/views/           # 页面
│   ├── src/api/             # Axios 封装
│   ├── Dockerfile
│   └── nginx.conf
│
├── docker-compose.yml        # Docker 部署编排
├── ARCHITECTURE.md           # 详细架构文档
└── .gitignore
```

---

## 📸 界面截图

> 将截图放入 `docs/screenshots/` 目录。

### 首页 & 个人资料
![首页](docs/screenshots/home.png)

### 个人相册
![相册](docs/screenshots/gallery.png)

### 个人衣橱
![衣橱](docs/screenshots/wardrobe.png)

### AI 搭配推荐
![搭配推荐](docs/screenshots/recommend.png)

### 创意写真
![创意写真](docs/screenshots/portrait.png)

### AI 穿搭评价
![穿搭评价](docs/screenshots/review.png)

---

## ⚙️ 配置说明

所有模型配置集中在 `backend/app/config.py`：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DEEPSEEK_MODEL` | 文本推理模型 | `deepseek-v4-flash` |
| `DASHSCOPE_VISION_MODEL` | 视觉理解模型 | `qwen3-vl-flash` |
| `DASHSCOPE_IMAGE_MODEL` | 图像生成模型 | `wan2.7-image` |
| `DASHSCOPE_IMAGE_MODEL_PRO` | 预览图生成模型 | `wan2.7-image-pro` |

---

## 🛡️ 数据说明

- 所有上传照片、生成图片存储在服务器 `uploads/` 目录
- 生成预览图 1 小时后自动清理
- 删除衣橱/相册数据后，风格画像自动归零重建
- API 密钥存放在 `backend/.env`，已加入 `.gitignore`

---

## 📄 License

MIT
