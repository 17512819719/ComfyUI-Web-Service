# ComfyUI Web Service

# 2025年6月24日小重构说明

本次重构主要内容如下：

- 实现了前后端彻底分离，后端代码、依赖、配置全部归档于 backend 目录，前端管理后台独立于 frontend/admin 目录
- 后端业务代码全部归档于 backend/app 包，import 路径已修正为相对导入，便于维护和扩展
- Redis 相关依赖已迁移至 backend/，后端依赖统一管理
- 移除了暂时用不到的 nginx 相关目录，项目结构更清晰
- 目录结构和启动方式已在文档中更新，便于新成员理解和使用

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![Celery](https://img.shields.io/badge/Celery-5.3+-orange.svg)
![Redis](https://img.shields.io/badge/Redis-3.2+-red.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**基于FastAPI和Celery的ComfyUI分布式AI服务**

[🚀 快速开始](#快速开始) • [📖 API文档](#api文档) • [⚙️ 配置说明](#配置说明) • [🔧 故障排除](#故障排除)

</div>

---

## 📋 目录

- [项目简介](#项目简介)
- [功能特性](#功能特性)
- [系统架构](#系统架构)
- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [API文档](#api文档)
- [客户端使用](#客户端使用)
- [故障排除](#故障排除)
- [开发指南](#开发指南)
- [更新日志](#更新日志)

## 🎯 项目简介

ComfyUI Web Service 是一个基于 FastAPI 和 Celery 的分布式 AI 服务，为 ComfyUI 提供 RESTful API 接口。支持文生图（Text-to-Image）和图生视频（Image-to-Video）功能，具备异步任务处理、进度监控、分布式节点支持等特性。

### 主要应用场景

- 🤖 AI 内容创作平台
- 🎨 图像生成服务
- 🎬 视频制作工具
- 🔄 批量图像处理
- 🌐 分布式 AI 推理

## ✨ 功能特性

| 功能模块 | 描述 | 状态 |
|---------|------|------|
| 🎨 **文生图** | 支持多种采样器和模型，可配置参数 | ✅ |
| 🎬 **图生视频** | 基于图像生成动态视频内容 | ✅ |
| 🔄 **异步处理** | Celery 任务队列，支持长时间运行任务 | ✅ |
| 📊 **进度监控** | 实时任务状态和进度查询 | ✅ |
| 🌐 **分布式支持** | 多节点 ComfyUI 服务负载均衡 | ✅ |
| 🔐 **身份认证** | JWT Token 认证机制 | ✅ |
| 📁 **文件管理** | 自动文件上传、下载和清理 | ✅ |
| 🚀 **服务管理** | 一键启动/停止所有服务 | ✅ |
| 📝 **API文档** | 自动生成的 Swagger 文档 | ✅ |
| 🖥️ **Web客户端** | 内置现代化 Web 界面 | ✅ |

## 🏗️ 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Client    │    │   FastAPI       │    │   Celery        │
│   (HTML/JS)     │◄──►│   (API Server)  │◄──►│   (Task Queue)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Redis         │    │   ComfyUI       │
                       │   (Cache/Queue) │    │   (AI Engine)   │
                       └─────────────────┘    └─────────────────┘
```

### 组件说明

- **FastAPI**: Web API 服务器，处理 HTTP 请求
- **Celery**: 异步任务队列，处理长时间运行的 AI 任务
- **Redis**: 消息代理和缓存存储
- **ComfyUI**: AI 模型推理引擎
- **Web Client**: 现代化 Web 界面，提供用户交互

## 📋 系统要求

### 最低配置

- **操作系统**: Windows 10/11, Linux, macOS
- **Python**: 3.8 或更高版本
- **内存**: 8GB RAM
- **存储**: 10GB 可用空间
- **网络**: 稳定的网络连接

### 推荐配置

- **操作系统**: Windows 11 或 Ubuntu 20.04+
- **Python**: 3.9 或更高版本
- **内存**: 16GB RAM 或更高
- **GPU**: NVIDIA GPU (8GB+ VRAM)
- **存储**: SSD 存储，50GB+ 可用空间

### 必需软件

- ✅ Python 3.8+
- ✅ ComfyUI (需要单独安装)
- ✅ Redis (已包含在项目中)
- ✅ 足够的 GPU 内存用于 AI 模型推理

## 🚀 快速开始

### 1. 环境准备

确保已安装 Python 3.8+ 和 ComfyUI：

```bash
# 检查 Python 版本
python --version

# 安装项目依赖
pip install -r requirements.txt
```

### 2. 配置 ComfyUI

编辑 `config.yaml` 文件，配置 ComfyUI 路径和端口：

```yaml
comfyui:
  port: 8188
  output_dir: "E:\\ComfyUI\\ComfyUI\\output"
```

### 3. 启动 ComfyUI 服务

**重要**: 必须先启动 ComfyUI 服务，再启动其他服务。

```bash
# 进入 ComfyUI 安装目录
cd E:\ComfyUI\ComfyUI

# 启动 ComfyUI 服务
python main.py --listen 0.0.0.0 --port 8188
```

### 4. 启动 Web Service

```bash
# 启动所有服务（Redis、Celery Worker、FastAPI）
python start_services.py
```

### 5. 访问服务

- **Web 客户端**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **ComfyUI 界面**: http://localhost:8188

### 6. 停止服务

```bash
# 停止 Web Service（Redis、Celery Worker、FastAPI）
python stop_services.py

# 手动停止 ComfyUI 服务
# 在 ComfyUI 终端按 Ctrl+C
```

## ⚙️ 配置说明

### 配置文件结构

```yaml
# ComfyUI 配置
comfyui:
  port: 8188                    # ComfyUI 服务端口
  output_dir: "E:\\ComfyUI\\ComfyUI\\output"  # 输出目录

# 文生图配置
text_to_image:
  ckpt_name: realisticVisionV60B1_v51HyperVAE.safetensors  # 模型文件
  sampler_name: euler          # 采样器
  scheduler: normal            # 调度器
  default_width: 512           # 默认宽度
  default_height: 512          # 默认高度
  default_steps: 20            # 默认步数
  default_cfg_scale: 7.0       # 默认 CFG 比例

# 图生视频配置
image_to_video:
  model_name: realisticVisionV60B1_v51HyperVAE.safetensors  # 模型文件
  default_fps: 8               # 默认帧率
  default_duration: 5.0        # 默认时长
  default_motion_strength: 0.8 # 默认运动强度
```

### 环境变量

| 变量名 | 默认值 | 描述 |
|--------|--------|------|
| `COMFYUI_PORT` | 8188 | ComfyUI 服务端口 |
| `REDIS_URL` | redis://localhost:6379/0 | Redis 连接地址 |
| `API_HOST` | 0.0.0.0 | API 服务器主机 |
| `API_PORT` | 8000 | API 服务器端口 |

## 📖 API文档

### 认证

所有 API 请求都需要 Bearer Token 认证：

```bash
# 登录获取 Token
curl -X POST "http://localhost:8000/api/auth/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=z&password=z"

# 使用 Token
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/endpoint
```

### 文生图 API

#### 提交生成任务

```bash
curl -X POST "http://localhost:8000/api/generate/image" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "prompt=a beautiful landscape&width=512&height=512"
```

**请求参数**:

| 参数 | 类型 | 必需 | 默认值 | 描述 |
|------|------|------|--------|------|
| `prompt` | string | ✅ | - | 正向提示词 |
| `negative_prompt` | string | ❌ | "" | 负向提示词 |
| `width` | integer | ❌ | 512 | 图像宽度 |
| `height` | integer | ❌ | 512 | 图像高度 |
| `steps` | integer | ❌ | 20 | 采样步数 |
| `cfg_scale` | float | ❌ | 7.0 | CFG 比例 |
| `seed` | integer | ❌ | -1 | 随机种子 |
| `batch_size` | integer | ❌ | 1 | 批量大小 |

**响应示例**:

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "任务已提交到队列"
}
```

### 图生视频 API

#### 提交视频生成任务

```bash
curl -X POST "http://localhost:8000/api/generate/video" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -F "image=@input.jpg" \
     -F "duration=5.0" \
     -F "fps=8"
```

**请求参数**:

| 参数 | 类型 | 必需 | 默认值 | 描述 |
|------|------|------|--------|------|
| `image` | file | ✅ | - | 输入图像文件 |
| `duration` | float | ❌ | 5.0 | 视频时长（秒） |
| `fps` | integer | ❌ | 8 | 帧率 |
| `motion_strength` | float | ❌ | 0.8 | 运动强度 |

### 任务状态 API

#### 查询任务状态

```bash
curl -X GET "http://localhost:8000/api/task/status/TASK_ID" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

**响应示例**:

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": 75,
  "message": "正在生成图像...",
  "result_url": null,
  "error_message": null
}
```

#### 下载结果

```bash
curl -X GET "http://localhost:8000/api/download/TASK_ID" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -o "result.png"
```

### 系统状态 API

#### 健康检查

```bash
curl -X GET "http://localhost:8000/api/health"
```

## 🖥️ 客户端使用

项目内置了现代化的 Web 客户端，提供直观的用户界面：

### 访问客户端

1. 启动服务后，访问 http://localhost:8000
2. 使用默认账号登录：
   - 用户名: `z`
   - 密码: `z`

### 功能特性

- 🎨 **文生图界面**: 直观的参数配置和实时预览
- 🎬 **图生视频界面**: 拖拽上传和参数调整
- 📊 **任务监控**: 实时任务状态和进度显示
- 📁 **文件管理**: 结果文件下载和管理
- 🔄 **批量处理**: 支持批量图像生成

## 🔧 故障排除

### 常见问题

#### 1. ComfyUI 启动失败

**症状**: 启动脚本提示 "ComfyUI 服务未运行"

**解决方案**:
```bash
# 1. 检查 ComfyUI 是否正确安装
ls E:\ComfyUI\ComfyUI\main.py

# 2. 手动启动 ComfyUI
cd E:\ComfyUI\ComfyUI
python main.py --listen 0.0.0.0 --port 8188

# 3. 验证服务状态
curl http://localhost:8188/system_stats
```

#### 2. Redis 启动失败

**症状**: Redis 服务无法启动

**解决方案**:
```bash
# 1. 检查 Redis 文件是否存在
ls Redis-x64-3.2.100/redis-server.exe

# 2. 手动启动 Redis
Redis-x64-3.2.100\redis-server.exe

# 3. 验证 Redis 连接
python -c "import redis; r=redis.Redis(); r.ping()"
```

#### 3. 端口冲突

**症状**: 端口被占用错误

**解决方案**:
```bash
# 1. 检查端口占用
netstat -ano | findstr :8188
netstat -ano | findstr :8000

# 2. 修改配置文件中的端口
# 编辑 config.yaml 文件

# 3. 停止占用端口的进程
taskkill /PID <进程ID> /F
```

#### 4. GPU 内存不足

**症状**: CUDA out of memory 错误

**解决方案**:
- 减少 `batch_size` 参数
- 降低图像分辨率
- 关闭其他 GPU 应用程序
- 使用 CPU 模式（如果支持）

#### 5. 模型文件缺失

**症状**: 模型加载失败

**解决方案**:
```bash
# 1. 检查模型文件路径
ls E:\ComfyUI\ComfyUI\models\checkpoints\

# 2. 下载所需模型文件
# 将模型文件放入 ComfyUI/models/checkpoints/ 目录

# 3. 更新配置文件中的模型名称
# 编辑 config.yaml 文件
```

### 日志调试

#### 查看服务日志

```bash
# FastAPI 日志
tail -f logs/fastapi.log

# Celery Worker 日志
tail -f logs/celery.log

# ComfyUI 日志
# 查看 ComfyUI 控制台输出
```

#### 启用调试模式

```bash
# 启动调试模式
python start_services.py --debug

# 或手动启动带详细日志
uvicorn main:app --reload --log-level debug
```

### 性能优化

#### 系统优化建议

1. **GPU 优化**:
   - 使用最新显卡驱动
   - 启用 CUDA 优化
   - 监控 GPU 温度和功耗

2. **内存优化**:
   - 增加系统内存
   - 使用 SSD 存储
   - 定期清理临时文件

3. **网络优化**:
   - 使用有线网络连接
   - 配置合适的防火墙规则
   - 优化网络延迟

## 👨‍💻 开发指南

### 项目结构

```
ComfyUI-Web-Service/
│
├── backend/                # 后端代码（FastAPI等）
│   ├── app/                # 业务代码（API、models、utils等）
│   ├── workflows/          # 工作流配置
│   ├── outputs/            # 输出目录
│   ├── uploads/            # 上传目录
│   ├── nginx-1.27.5/       # nginx相关
│   ├── Redis-x64-3.2.100/  # redis相关
│   ├── config.yaml         # 配置文件
│   ├── requirements.txt    # Python依赖
│   └── ...
│
├── frontend/               # 前端代码（Vue项目）
│   ├── admin/              # 管理后台前端
│   └── ...
│
├── docker-compose.yml
├── Dockerfile
└── ...
```

### 开发环境设置

```bash
# 1. 克隆项目
git clone <repository-url>
cd ComfyUI-Web-Service

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 安装开发依赖
pip install pytest black flake8 mypy

# 5. 配置开发环境
cp config.yaml.example config.yaml
# 编辑 config.yaml
```

### 代码规范

```bash
# 代码格式化
black .

# 代码检查
flake8 .

# 类型检查
mypy .

# 运行测试
pytest
```

### 添加新功能

1. **添加新的 API 端点**:
   - 在 `main.py` 中定义路由
   - 在 `models.py` 中定义数据模型
   - 在 `tasks.py` 中定义 Celery 任务

2. **添加新的 ComfyUI 工作流**:
   - 在 `workflows/` 目录中添加 JSON 文件
   - 在 `tasks.py` 中实现工作流逻辑

3. **扩展客户端功能**:
   - 修改 `Client/Client-ComfyUI.html`
   - 添加新的 JavaScript 函数
   - 更新 CSS 样式

### 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📝 更新日志

### 🆕 最近更新

- 重构文生图工作流模块，工作流不再硬编码，通过特定 workflow json 文件实现，支持自定义和扩展。
- 新增 `workflow_manager.py`、`workflow_selector.py`，支持多工作流配置和选择。
- workflows 目录结构调整，支持多种工作流 json 文件。

### 🗂️ 工作流模块说明

- `workflow_manager.py`：用于加载和管理不同的工作流配置。
- `workflow_selector.py`：用于选择和切换当前使用的工作流。
- `workflows/`：存放所有可用的工作流 json 文件，支持自定义扩展。

### v1.2.0 (2024-01-XX)

#### 🚀 新功能
- ✨ 重构服务管理方式，ComfyUI 需要手动启动
- ✨ 改进服务状态检测和错误处理
- ✨ 优化配置文件结构和参数验证

#### 🔧 改进
- 🔄 简化启动流程，提高稳定性
- 📝 更新文档和故障排除指南
- 🐛 修复多个已知问题

#### 🐛 修复
- 修复服务启动顺序问题
- 修复配置文件加载错误
- 修复任务状态更新问题

### v1.1.0 (2024-01-XX)

#### 🚀 新功能
- ✨ 新增 ComfyUI 服务自动检测和启动
- ✨ 新增配置文件支持
- ✨ 改进服务管理脚本
- ✨ 新增服务状态检测功能

#### 🔧 改进
- 🔄 优化任务队列管理
- 📊 改进进度监控机制
- 🛡️ 增强错误处理和日志记录

### v1.0.0 (2024-01-XX)

#### 🎉 初始版本
- ✨ 基础文生图和图生视频功能
- ✨ FastAPI + Celery 架构
- ✨ Redis 缓存支持
- ✨ JWT 认证机制
- ✨ Web 客户端界面

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🤝 支持

如果您遇到问题或有建议，请：

1. 📖 查看 [故障排除](#故障排除) 部分
2. 🔍 搜索 [Issues](../../issues)
3. 💬 创建新的 Issue
4. 📧 联系维护者

---

<div align="center">

**Made with ❤️ by the ComfyUI Web Service Team**

[⭐ Star this project](https://github.com/your-repo/comfyui-web-service)

</div>

## 目录结构（前后端分离重构后）

```
ComfyUI-Web-Service/
│
├── backend/                # 后端代码（FastAPI等）
│   ├── app/                # 业务代码（API、models、utils等）
│   ├── workflows/          # 工作流配置
│   ├── outputs/            # 输出目录
│   ├── uploads/            # 上传目录
│   ├── nginx-1.27.5/       # nginx相关
│   ├── Redis-x64-3.2.100/  # redis相关
│   ├── config.yaml         # 配置文件
│   ├── requirements.txt    # Python依赖
│   └── ...
│
├── frontend/               # 前端代码（Vue项目）
│   ├── admin/              # 管理后台前端
│   └── ...
│
├── docker-compose.yml
├── Dockerfile
└── ...
```

## 说明
- `backend/`：后端服务，包含API、业务逻辑、配置、第三方服务等。
- `frontend/`：前端项目，推荐使用 Vue3 + Vite。

---

> 本项目已重构为前后端分离结构，便于开发和维护。

## 后端管理API（/admin）
- `/admin/login`：管理员登录，返回JWT token
- `/admin/workflows`：获取所有工作流列表
- `/admin/workflow_config?name=xxx`：获取指定工作流参数
- `/admin/module_config?module=xxx`：获取模块配置
- `/admin/module_config`（POST）：设置模块配置
- 需在 `backend/admin_config.yaml` 设置管理员密码
- 需在 `main.py` 挂载 `admin_api.router`（已自动完成）

## 前端管理后台开发结构
- 采用 Vue3 + Vite，代码在 `frontend/admin/`
- 页面结构：
  - `src/views/Login.vue` 管理员登录页
  - `src/views/AdminHome.vue` 管理主页面（可扩展为多模块管理）
  - `src/router/index.js` 路由配置，支持登录保护
  - `src/axios.js` 全局axios拦截器，自动带token，401跳转登录
- 推荐开发流程：
  1. 登录页调用 `/admin/login` 获取token，存localStorage
  2. 主页面通过token访问管理API，支持工作流/模块配置管理
  3. 可根据实际需求扩展更多管理功能和UI

## 启动方式
- 后端：
  - `start_all.bat`/`stop_all.bat` 支持任意目录自动切换，推荐直接双击或命令行运行
  - 或手动 `cd backend && python start_services.py`
- 前端：
  - `cd frontend/admin && npm install && npm run dev`
  - 浏览器访问 http://localhost:5173/
- Docker：
  - `docker-compose up --build` 支持一键启动后端服务

---

> 项目结构、启动方式、管理后台API和前端开发流程均已标准化，适合团队协作和持续扩展。