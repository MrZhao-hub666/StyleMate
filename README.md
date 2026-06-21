<p align="center">
  <h1 align="center">👔 StyleMate</h1>
  <p align="center">您的专属 AI 穿搭顾问 — 拍照即分析，一键试穿预览</p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.13-blue?logo=python" alt="Python 3.13">
  <img src="https://img.shields.io/badge/vue-3.x-green?logo=vue.js" alt="Vue 3">
  <img src="https://img.shields.io/badge/fastapi-0.136-teal?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/license-MIT-yellow" alt="License MIT">
  <img src="https://img.shields.io/badge/docker-compose-blue?logo=docker" alt="Docker">
</p>

<p align="center">
  <a href="#-功能一览"><strong>功能</strong></a> ·
  <a href="#-快速开始本地开发"><strong>快速开始</strong></a> ·
  <a href="#-云端部署"><strong>云端部署</strong></a> ·
  <a href="#-技术架构"><strong>架构</strong></a> ·
  <a href="#-项目结构"><strong>目录</strong></a> ·
  <a href="#-配置说明"><strong>配置</strong></a> ·
  <a href="#-截图"><strong>截图</strong></a> ·
  <a href="#-常见问题"><strong>FAQ</strong></a>
</p>

---

## 🎯 功能一览

| 功能 | 说明 |
| --- | --- |
| 📸 **个人相册** | 上传照片 → YOLO 识别人脸和衣物，自动打标签 |
| 👗 **个人衣橱** | 拍照入库 → YOLO 分析颜色/图案/面料 → 视觉大模型精校，精确到领型袖型 |
| 🧠 **风格画像** | 自动聚合历史数据，学习颜色偏好、穿搭风格，删数据自动归零重建 |
| ✨ **AI 搭配推荐** | 选场合 → DeepSeek 出 3 套方案 → 万相 2.7-Pro 生成上身试穿预览图，三联可下载 |
| 🎨 **创意写真** | 上传照片 + 描述 → AI 保留人脸，换装换场景，一键保存到相册 |
| 📝 **AI 穿搭评价** | 拍照当前穿搭 → YOLO 参考 + 视觉模型看图打分，亮点/不足/建议一目了然 |

---

## 🚀 快速开始（本地开发）

### 环境要求

- **Python** ≥ 3.13
- **Node.js** ≥ 18
- **uv**（Python 包管理器）: `pip install uv`
- 边端服务需要本地算力（摄像头 + CPU/GPU）

### 1. 克隆项目

```bash
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

### 3. 安装依赖

```bash
cd edge && uv sync             # 边端 Python 依赖 + 自动下载 YOLO 模型
cd ../backend && uv sync        # 后端 Python 依赖
cd ../frontend && npm install   # 前端 Node 依赖
```

### 4. 启动服务

打开三个终端：

```bash
# 终端 1 — 边端 YOLO 分析服务 (:9001)
cd edge && uv run uvicorn server:app --host 0.0.0.0 --port 9001 --reload

# 终端 2 — 后端 API (:9000)
cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload

# 终端 3 — 前端开发服务器 (:5173)
cd frontend && npm run dev
```

浏览器打开 `http://localhost:5173` 即可使用。

> 💡 **提示**：YOLO 默认使用 ultralytics 预训练权重 + 几何估算。如需更高精度，可用自己的衣物标注数据微调后替换。

---

## ☁️ 云端部署

### 前置条件

- 一台云服务器（2 核 4G 以上），已安装 Docker & Docker Compose
- 边端 YOLO 服务在用户本机运行

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

### 🖥️ 本机启动边端

边端 YOLO 分析服务需要在用户本机运行（需要摄像头 + 本地算力）：

```bash
cd edge
uv sync                      # 首次安装依赖（自动下载 YOLO 模型）
uv run uvicorn server:app --host 0.0.0.0 --port 9001
```

### 🔗 关联前后端

云部署时，边端调用由浏览器（前端）直接发起，避免服务器访问本机局域网的网络限制：

1. 评价/分析时，前端先调用本机 `http://localhost:9001` 边端分析
2. 拿到结果后再发送给云端后端
3. 无需修改 `EDGE_URL`（默认值为 `http://localhost:9001`）

---

## 🏗️ 技术架构

```
┌── 云服务器 ──────────────────┐          ┌── 用户本机 ──┐
│                              │          │               │
│  前端 Nginx (:80)            │  HTTP    │  浏览器       │
│   ↓ reverse proxy /api       │←────────→│  ↓            │
│  后端 FastAPI (:9000)        │          │  边端 YOLO    │
│   ↓ DeepSeek / Qwen / 万相   │          │  (:9001)      │
│                              │          │               │
└──────────────────────────────┘          └───────────────┘
```

### 技术栈

| 层级 | 技术 | 说明 |
| --- | --- | --- |
| **前端** | Vue 3 + Vite + Element Plus + Pinia | SPA 单页应用，响应式 UI |
| **后端** | FastAPI + SQLAlchemy (async) + LangChain | 异步 API，ORM，LLM Agent 编排 |
| **边端** | FastAPI + YOLO (ultralytics) + OpenCV | 本地 CV 分析，七维衣物属性提取 |
| **数据库** | SQLite (aiosqlite) + ChromaDB | 关系存储 + 向量知识库 |
| **部署** | Docker + Nginx + docker compose | 容器化一键部署 |

### 模型分工

| 模型 | 服务商 | 用途 |
| --- | --- | --- |
| DeepSeek `deepseek-v4-flash` | deepseek.com | 搭配推荐推理、写真 prompt 优化 |
| 通义千问 `qwen3-vl-flash` | 阿里 DashScope | 穿搭视觉评价、衣橱云端校验 |
| 万相 2.7-Pro | 阿里 DashScope | 上身试穿预览、创意写真生成 |
| sentence-transformers | 本地 | 知识库向量检索 |

详细数据流向见 [ARCHITECTURE.md](ARCHITECTURE.md)。

---

## 📁 项目结构

```
StyleMate/
├── backend/                    # 云端后端 (FastAPI :9000)
│   ├── app/
│   │   ├── api/                # 接口层 (相册/衣橱/搭配/写真/评价)
│   │   ├── agent/              # LLM Agent (搭配推理/写真优化/评价)
│   │   ├── services/           # 服务层 (生图/天气/风格画像/定时清理)
│   │   ├── models/             # SQLAlchemy 模型
│   │   ├── knowledge/          # 知识库 (ChromaDB 向量检索)
│   │   └── config.py           # 统一配置入口
│   ├── .env.example            # 密钥模板
│   ├── pyproject.toml          # Python 项目配置 + 依赖
│   ├── uv.lock                 # 依赖锁定文件
│   └── Dockerfile
│
├── edge/                       # 边端 YOLO (本机运行 :9001)
│   ├── server.py               # HTTP 分析服务
│   ├── detector.py             # YOLO 人体检测 + 衣物区域提取
│   ├── attribute_pipeline.py   # 七维属性解析流水线
│   ├── color_analyzer.py       # K-means 颜色提取
│   ├── texture_analyzer.py     # 图案面料分析 (Gabor/GLCM)
│   ├── pyproject.toml
│   └── uv.lock
│
├── frontend/                   # 前端 (Vue 3 + Vite)
│   ├── src/views/              # 页面组件
│   ├── src/api/                # Axios 请求封装
│   ├── src/stores/             # Pinia 状态管理
│   ├── Dockerfile
│   └── nginx.conf
│
├── docker-compose.yml          # Docker 编排 (后端 + 前端)
├── ARCHITECTURE.md             # 详细架构文档
├── .gitignore
└── README.md
```

---

## ⚙️ 配置说明

所有模型配置集中在 [backend/app/config.py](backend/app/config.py)：

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `DEEPSEEK_MODEL` | 文本推理模型 | `deepseek-v4-flash` |
| `DASHSCOPE_VISION_MODEL` | 视觉理解模型 | `qwen3-vl-flash` |
| `DASHSCOPE_IMAGE_MODEL` | 图像生成模型 | `wan2.7-image` |
| `DASHSCOPE_IMAGE_MODEL_PRO` | 预览图生成模型 | `wan2.7-image-pro` |
| `EDGE_URL` | 边端分析服务地址 | `http://localhost:9001` |
| `DATABASE_URL` | 数据库连接 | `sqlite+aiosqlite:///stylemate.db` |
| `MAX_UPLOAD_SIZE` | 上传文件大小上限 | 10 MB |

### PyPI 镜像源

项目默认使用阿里云 PyPI 镜像加速依赖安装。如需修改，编辑 `backend/pyproject.toml` 和 `edge/pyproject.toml` 中的 `[[tool.uv.index]]` 配置段。

---

## 📸 界面截图

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

## 🛡️ 数据说明

- 所有上传照片、生成图片存储在服务器 `uploads/` 目录
- 生成预览图 1 小时后自动清理
- 删除衣橱/相册数据后，风格画像自动归零重建
- API 密钥存放在 `backend/.env`，已加入 `.gitignore`

---

## 🔧 常见问题

### Docker 构建时 PyPI 下载失败 (403/连接超时)

清华 PyPI 镜像可能对某些包（如 `huggingface-hub`）返回 403。项目默认已配置阿里云镜像 + 官方 PyPI 兜底。

如仍有问题，在服务器上重新拉取最新代码重建：

```bash
git pull
docker compose build --no-cache backend
docker compose up -d
```

### 边端连接失败

确保边端服务在本机已启动：
```bash
curl http://localhost:9001/health
```

如果后端日志显示连接拒绝，检查 `EDGE_URL` 配置是否正确。

### Docker 提示 `version` 属性过时

已修复。如果旧版本仍有警告，手动删除 `docker-compose.yml` 中的 `version: "3.8"` 行即可（不影响运行）。

### 上传大图失败

默认限制 10 MB，可在 `backend/app/config.py` 中修改 `MAX_UPLOAD_SIZE`。

---

## 📄 License

MIT — 详见 [LICENSE](LICENSE) 文件。
