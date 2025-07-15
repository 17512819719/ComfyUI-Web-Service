# ComfyUI Web Service

一个基于 FastAPI 和 Celery 的 ComfyUI 分布式 Web 服务系统，支持多种 AI 内容生成任务的统一管理和调度。

## 🌟 特性

- **多模态内容生成**: 支持文生图、SDXL 等多种 AI 生成任务
- **分布式架构**: 支持一台主机调度器 + 多台从机ComfyUI节点的分布式部署
- **智能负载均衡**: 多种负载均衡策略，自动任务分发和故障转移
- **节点管理**: 自动节点发现、健康检查、状态监控
- **配置驱动**: 通过 YAML 配置文件管理工作流和参数映射
- **RESTful API**: 完整的 REST API 接口，支持任务提交、状态查询、结果获取
- **Web 界面**: 提供美观的 HTML 客户端和 Vue.js 管理后台
- **实时监控**: WebSocket 实时任务进度监控和集群状态监控
- **任务管理**: 支持任务优先级、批量处理、状态追踪
- **局域网访问**: 支持局域网内多设备访问
- **高可用性**: 故障自动检测、任务重新分配、服务自愈
- **身份认证**: 支持客户端身份认证和访问控制
- **数据库支持**: 集成MySQL数据库，支持任务历史和用户管理
- **图生视频**: 支持图像到视频的转换功能
- **SDXL支持**: 完整支持SDXL模型的文生图功能
- **数据同步**: 支持多节点间的数据自动同步

## 🏗️ 系统架构

### 分布式架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Client    │    │  Vue.js Admin   │    │   Mobile App    │
│   (HTML/JS)     │    │   Dashboard     │    │   (Future)      │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────┐
│                    主机调度器 (Master)                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   API Gateway   │  │  Task Scheduler │  │  Node Manager   │ │
│  │   (FastAPI)     │  │   (Celery)      │  │   (Registry)    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Load Balancer   │  │ Health Monitor  │  │ Config Manager  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┼───────────┐
                    │           │           │
            ┌───────▼───┐ ┌─────▼─────┐ ┌───▼───────┐
            │ComfyUI-1  │ │ComfyUI-2  │ │ComfyUI-N  │
            │(Worker)   │ │(Worker)   │ │(Worker)   │
            └───────────┘ └───────────┘ └───────────┘
```

### 核心组件

- **API Gateway**: 统一API入口，处理认证和路由
- **Task Scheduler**: 基于Celery的异步任务调度器
- **Node Manager**: 节点注册、发现和状态管理
- **Load Balancer**: 智能负载均衡和任务分发
- **Health Monitor**: 节点健康检查和故障检测
- **Config Manager**: 配置管理和热更新

## 📋 系统要求

### 硬件要求
- **GPU**: NVIDIA GPU (推荐 8GB+ VRAM)
- **内存**: 16GB+ RAM
- **存储**: 50GB+ 可用空间

### 软件要求
- **Python**: 3.10+
- **ComfyUI**: 最新版本
- **Redis**: 3.2.100+
- **MySQL**: 8.0+
- **Node.js**: 16+ (用于前端开发)

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd ComfyUI-Web-Service

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r backend/requirements.txt
```

### 2. 数据库配置

在启动服务之前，需要先配置并初始化数据库：

```bash
# 1. 确保MySQL服务已启动

# 2. 执行数据库初始化脚本
cd database
mysql -u your_username -p < setup_databases.sql
mysql -u your_username -p < migrations/add_client_auth_fields.sql

# 3. 配置数据库连接
# 编辑 backend/config.yaml 添加数据库配置：
```

```yaml
# 数据库配置
database:
  host: "localhost"
  port: 3306
  user: "your_username"
  password: "your_password"
  database: "comfyui_service"
```

### 3. 身份认证配置

编辑 `backend/config.yaml` 添加认证配置：

```yaml
# 认证配置
auth:
  enable_client_auth: true
  token_expire_minutes: 1440  # 24小时
  secret_key: "your-secret-key"
```

### 4. 配置系统

编辑 `backend/config.yaml` 文件：

```yaml
# ComfyUI配置
comfyui:
  host: "127.0.0.1"
  port: 8188
  output_dir: "outputs"  # 输出目录，支持相对路径和绝对路径

# Redis配置
redis:
  host: "localhost"
  port: 6379
  db: 0

# 工作流配置
task_types:
  text_to_image:
    workflows:
      sd_basic:
        workflow_file: "workflows/text_to_image/文生图.json"  # 支持相对路径
```

### 5. 启动服务

#### 单机模式

使用一键启动脚本：

```bash
# Windows
start_all.bat

# 或手动启动
cd backend
python -m uvicorn app.main_v2:app --host 0.0.0.0 --port 8000
```

#### 分布式模式

1. **配置分布式节点**

编辑 `backend/config.yaml`：

```yaml
# 分布式节点配置
nodes:
  discovery_mode: "static"

  # 负载均衡配置
  load_balancing:
    strategy: "least_loaded"  # 负载均衡策略
    enable_failover: true
    max_retries: 3

  # 静态节点配置
  static_nodes:
    - node_id: "comfyui-worker-1"
      host: "192.168.1.101"  # 从机IP地址
      port: 8188
      max_concurrent: 4
      capabilities: ["text_to_image"]
      metadata:
        location: "worker-server-1"
        gpu_model: "RTX 4090"
```

2. **启动主机调度器**

```bash
# Windows
start_distributed.bat

# 或手动启动
cd backend
python -m uvicorn app.main_v2:app --host 0.0.0.0 --port 8000
```

3. **启动从机ComfyUI**

在每台从机服务器上：

```bash
# 启动ComfyUI服务
cd ComfyUI
python main.py --listen 0.0.0.0 --port 8188
```

4. **验证部署**

```bash
# 运行系统验证脚本
cd backend
python verify_system.py

# 运行分布式功能测试
python test_distributed.py
```

详细的分布式部署指南请参考：[DISTRIBUTED_DEPLOYMENT.md](DISTRIBUTED_DEPLOYMENT.md)

### 6. 访问服务

- **Web 客户端**: http://localhost:8000/client 或打开 `Client/Client-ComfyUI.html`
- **管理后台**: http://localhost:8000/admin (Vue.js管理界面，支持节点管理)
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/api/health

#### 管理后台功能

- 📊 **仪表板**: 系统概览和实时统计
- 🖥️ **节点管理**: 查看节点状态、负载、健康检查
- 📋 **任务管理**: 任务列表、状态监控、历史记录
- 👥 **用户管理**: 用户权限和访问控制
- ⚙️ **系统配置**: 负载均衡策略、系统参数

## 📁 项目结构

```
ComfyUI-Web-Service/
├── backend/                    # 后端服务
│   ├── app/                   
│   │   ├── admin_api/        # 管理后台API
│   │   ├── api/              # 客户端API
│   │   ├── auth/             # 认证相关
│   │   ├── core/             # 核心业务逻辑
│   │   ├── database/         # 数据库模型和DAO
│   │   ├── processors/       # 任务处理器
│   │   ├── queue/           # Celery任务队列
│   │   ├── services/        # 业务服务层
│   │   └── utils/           # 工具函数
├── database/                 # 数据库脚本
│   ├── migrations/          # 数据库迁移脚本
│   ├── setup_databases.sql  # 数据库初始化
│   └── README.md           # 数据库说明
├── frontend/                 # 前端项目
│   └── admin/               # Vue.js 管理后台
├── Client/                  # HTML 客户端
├── scripts/                 # 启动和管理脚本
├── start_all.bat           # 一键启动脚本
└── README.md               # 项目文档
```

## 🔧 配置说明

### 工作流配置

系统通过配置文件管理工作流参数映射：

```yaml
task_types:
  text_to_image:
    workflows:
      sd_basic:
        workflow_file: "path/to/workflow.json"
        parameter_mapping:
          prompt:
            node_id: "314"
            input_name: "text"
            default_value: ""
          width:
            node_id: "135"
            input_name: "width"
            default_value: 512
```

### 参数优先级

1. **前端提交参数** (最高优先级)
2. **配置文件默认值**
3. **工作流原始值** (最低优先级)

## 🔐 身份认证

### 客户端认证

```bash
# 1. 创建客户端
POST /api/v2/auth/register
{
  "client_name": "test_client",
  "description": "测试客户端"
}

# 2. 获取访问令牌
POST /api/v2/auth/token
{
  "client_id": "your_client_id",
  "client_secret": "your_client_secret"
}
```

### 管理后台认证

```bash
POST /admin/auth/login
{
  "username": "admin",
  "password": "admin"
}
```

## 📡 新增API接口

### 图生视频接口

```bash
POST /api/v2/tasks/image-to-video
Content-Type: application/json
Authorization: Bearer <token>

{
  "image_path": "path/to/image.png",
  "duration": 30,
  "fps": 30,
  "workflow_name": "image_to_video_basic"
}
```

### SDXL文生图接口

```bash
POST /api/v2/tasks/text-to-image-sdxl
Content-Type: application/json
Authorization: Bearer <token>

{
  "prompt": "a beautiful landscape",
  "negative_prompt": "blurry, low quality",
  "width": 1024,
  "height": 1024,
  "workflow_name": "sdxl_basic"
}
```

## 🔍 监控和调试

### 性能监控

```bash
# 查看节点性能指标
GET /api/v2/admin/performance/nodes

# 查看任务执行统计
GET /api/v2/admin/performance/tasks
```

### 日志管理

- 系统日志: `backend/logs/system.log`
- 访问日志: `backend/logs/access.log`
- 错误日志: `backend/logs/error.log`
- Celery 日志: `backend/logs/celery.log`

## 🚨 故障排除

### 常见问题

1. **ComfyUI 连接失败**
   - 检查 ComfyUI 是否正常运行
   - 验证配置文件中的 host 和 port

2. **Redis 连接失败**
   - 确保 Redis 服务已启动
   - 检查防火墙设置

3. **工作流执行失败**
   - 检查工作流文件路径
   - 验证参数映射配置
   - 查看 Celery Worker 日志

4. **数据库连接问题**
   - 检查MySQL服务状态
   - 验证数据库用户权限
   - 确认连接字符串正确

5. **认证失败**
   - 检查token是否过期
   - 验证client_id和client_secret
   - 确认请求头格式正确

### 性能优化

- 调整 Celery Worker 数量
- 配置 Redis 内存限制
- 优化工作流参数

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 发起 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) - 强大的 AI 图像生成工具
- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的 Python Web 框架
- [Celery](https://docs.celeryproject.org/) - 分布式任务队列
- [Vue.js](https://vuejs.org/) - 渐进式 JavaScript 框架
