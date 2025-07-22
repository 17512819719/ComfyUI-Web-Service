# ComfyUI Web Service

一个基于 FastAPI 和 Celery 的 ComfyUI 分布式 Web 服务系统，支持多种 AI 内容生成任务的统一管理和调度。

## 📋 快速导航

- [🚀 快速开始](#-快速开始) - Docker 一键部署 / 传统部署
- [🗄️ 数据库管理](#️-数据库管理) - 迁移系统和数据库架构
- [🐳 Docker 部署](#-docker-部署) - 容器化部署指南
- [⚙️ 配置说明](#️-配置说明) - 系统配置和工作流管理
- [🌐 访问服务](#-访问服务) - 服务地址和功能介绍
- [📁 项目结构](#-项目结构) - 完整的目录结构说明
- [🔧 高级功能](#-高级功能) - 数据库迁移、Docker管理等
- [🚨 故障排除](#-故障排除) - 常见问题和解决方案

## 🌟 特性

- 🎨 **多模态内容生成**: 支持文生图、SDXL、图生视频等多种 AI 生成任务
- 🏗️ **分布式架构**: 支持一台主机调度器 + 多台从机ComfyUI节点的分布式部署
- ⚖️ **智能负载均衡**: 多种负载均衡策略，自动任务分发和故障转移
- 🔧 **节点管理**: 自动节点发现、健康检查、状态监控
- 📝 **配置驱动**: 通过 YAML 配置文件管理工作流和参数映射
- 🌐 **RESTful API**: 完整的 REST API 接口，支持任务提交、状态查询、结果获取
- 💻 **双端界面**: HTML 客户端 + Vue.js 管理后台，支持局域网访问
- 📊 **实时监控**: WebSocket 实时任务进度监控和集群状态监控
- 📋 **任务管理**: 支持任务优先级、批量处理、状态追踪
- 🔐 **身份认证**: 客户端用户管理和会话控制
- 🗄️ **三数据库架构**: 客户端、管理端、共享数据分离存储
- 🔄 **数据库迁移**: 版本化的数据库结构管理，支持自动迁移
- 🐳 **完整容器化**: Docker + Docker Compose 一键部署
- 🚀 **高可用性**: 故障自动检测、任务重新分配、服务自愈

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
- **Database Migration**: 版本化数据库结构管理
- **Container Orchestration**: Docker 容器编排和部署

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
- **Docker**: 20.10+ (推荐容器化部署)
- **Docker Compose**: 2.0+ (支持 `docker compose` 和 `docker-compose`)
- **Node.js**: 16+ (用于前端开发)

## 🚀 快速开始

### 方式一：Docker 部署（推荐）

#### 1. 克隆项目
```bash
git clone <repository-url>
cd ComfyUI-Web-Service
```

#### 2. 配置环境变量
```bash
cd docker/
cp .env .env.local
# 编辑 .env.local 文件，修改数据库密码、ComfyUI节点地址等配置
```

#### 3. 一键部署
```bash
# 给脚本执行权限 (Linux/macOS)
chmod +x deploy.sh

# 构建并启动所有服务
./deploy.sh build
./deploy.sh start -d

# 查看服务状态
./deploy.sh status
```

**Windows 用户**: 在 Git Bash 或 WSL 中运行上述命令

#### 4. 访问服务
- 客户端界面: http://localhost:8001
- 管理后台: http://localhost:8002
- API 文档: http://localhost:8000/docs

### 方式二：传统部署

#### 1. 环境准备
```bash
# 克隆项目
git clone <repository-url>
cd ComfyUI-Web-Service

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt
```

#### 2. 数据库配置

配置 `backend/config.yaml` 中的数据库连接信息，然后初始化数据库：

```bash
# 使用数据库管理工具初始化
python database/tools/db_manager.py init

# 这会自动：
# 1. 创建数据库表结构
# 2. 执行所有迁移
# 3. 初始化默认数据
```

#### 3. 启动服务

```bash
# 启动 Redis
redis-server

# 启动 Celery Worker
cd backend
celery -A app.queue.celery_app worker --loglevel=info

# 启动 FastAPI 服务
cd backend
uvicorn app.main_v2:app --host 0.0.0.0 --port 8000 --reload

# 启动客户端服务
cd scripts
python start_client.py

# 启动管理后台服务
cd scripts
python start_admin.py

## 🗄️ 数据库管理

### 数据库架构

项目采用**三数据库分离架构**：

- **客户端数据库** (comfyui_client): 存储客户端用户数据和基础任务信息
- **管理后台数据库** (comfyui_admin): 存储系统管理、配置和监控数据
- **共享数据库** (comfyui_shared): 存储需要跨系统访问的核心数据

### 数据库迁移系统

项目包含完整的数据库迁移系统，支持版本化的数据库结构管理：

```bash
# 查看迁移状态
python database/tools/db_manager.py migration-status

# 运行迁移
python database/tools/db_manager.py migrate

# 创建新的迁移文件
python database/tools/create_migration.py create add_new_field --database client --description "添加新字段"
```

### 目录结构

```
database/
├── README.md                    # 数据库管理说明
├── schema/                      # 数据库结构文件
│   ├── client_database.sql      # 客户端数据库结构
│   ├── admin_database.sql       # 管理后台数据库结构
│   └── shared_database.sql      # 共享数据库结构
├── migrations/                  # 数据库迁移文件
└── tools/                       # 数据库管理工具
    ├── db_manager.py            # 主要数据库管理工具
    ├── migration_manager.py     # 迁移管理器
    └── create_migration.py      # 创建迁移文件工具
```

## 🐳 Docker 部署

### Docker Compose 配置

项目提供完整的 Docker 容器化解决方案：

```
docker/
├── Dockerfile                   # 主应用镜像
├── docker-compose.yml           # 开发环境配置
├── docker-compose.prod.yml      # 生产环境配置
├── deploy.sh                    # 部署管理脚本
├── start.sh                     # 容器启动脚本
├── .env                         # 环境变量模板
└── ...
```

### 部署命令

```bash
# 开发环境部署
cd docker/
./deploy.sh build
./deploy.sh start -d

# 生产环境部署
./deploy.sh -p build
./deploy.sh -p start -d

# 查看服务状态
./deploy.sh status

# 查看日志
./deploy.sh logs

# 运行数据库迁移
./deploy.sh migrate

# 备份数据
./deploy.sh backup /path/to/backup
```

### 服务端口

- **FastAPI 主服务**: http://localhost:8000
- **客户端界面**: http://localhost:8001
- **管理后台**: http://localhost:8002
- **API 文档**: http://localhost:8000/docs

## ⚙️ 配置说明

### 主配置文件

编辑 `backend/config.yaml` 文件：
```yaml
# MySQL 数据库配置
mysql:
  client:
    host: localhost
    port: 3306
    user: root
    password: "123456"
    database: comfyui_client
  admin:
    host: localhost
    port: 3306
    user: root
    password: "123456"
    database: comfyui_admin
  shared:
    host: localhost
    port: 3306
    user: root
    password: "123456"
    database: comfyui_shared

# Redis 配置
redis:
  host: localhost
  port: 6379
  db: 0

# ComfyUI 节点配置
nodes:
  static_nodes:
    - node_id: "comfyui-worker-1"
      host: "192.168.1.101"  # ComfyUI 服务器IP
      port: 8188
      max_concurrent: 4
      capabilities: ["text_to_image", "image_to_video"]

# 工作流配置
task_types:
  text_to_image:
    workflows:
      sd_basic:
        workflow_file: "workflows/text_to_image/文生图.json"
  image_to_video:
    workflows:
      svd_basic:
        workflow_file: "workflows/image_to_video/图生视频.json"
```

## 🌐 访问服务

### 服务地址

- **客户端界面**: http://localhost:8001
- **管理后台**: http://localhost:8002
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

### 管理后台功能

- 📊 **仪表板**: 系统概览和实时统计
- 🖥️ **节点管理**: 查看节点状态、负载、健康检查
- 📋 **任务管理**: 任务列表、状态监控、历史记录
- 👥 **用户管理**: 用户权限和访问控制
- ⚙️ **系统配置**: 负载均衡策略、系统参数
- 🗄️ **数据库管理**: 迁移状态、数据统计

## 📁 项目结构

```
ComfyUI-Web-Service/
├── README.md                           # 项目说明
├── requirements.txt                    # Python依赖
├── backend/                            # 后端应用
│   ├── config.yaml                     # 主配置文件
│   ├── app/                            # 应用核心代码
│   │   ├── admin_api/                  # 管理后台API
│   │   ├── api/                        # 客户端API
│   │   ├── auth/                       # 认证相关
│   │   ├── core/                       # 核心业务逻辑
│   │   ├── database/                   # 数据库模型和连接
│   │   ├── processors/                 # 任务处理器
│   │   ├── queue/                      # Celery任务队列
│   │   ├── services/                   # 业务服务层
│   │   └── utils/                      # 工具函数
│   ├── outputs/                        # 生成文件输出目录
│   ├── uploads/                        # 用户上传文件目录
│   └── workflows/                      # ComfyUI工作流文件
├── frontend/                           # 前端应用
│   ├── client/                         # 客户端界面
│   └── admin/                          # 管理后台界面 (Vue.js)
├── database/                           # 数据库管理 ⭐
│   ├── README.md                       # 数据库使用说明
│   ├── setup_databases.sql             # 数据库初始化脚本
│   ├── schema/                         # 数据库结构文件
│   │   ├── client_database.sql         # 客户端数据库结构
│   │   ├── admin_database.sql          # 管理后台数据库结构
│   │   └── shared_database.sql         # 共享数据库结构
│   ├── migrations/                     # 数据库迁移文件
│   └── tools/                          # 数据库管理工具
│       ├── db_manager.py               # 主要数据库管理工具
│       ├── migration_manager.py        # 迁移管理器
│       └── create_migration.py         # 创建迁移文件工具
├── docker/                             # Docker容器化配置 ⭐
│   ├── Dockerfile                      # 主应用镜像
│   ├── docker-compose.yml             # 开发环境配置
│   ├── docker-compose.prod.yml        # 生产环境配置
│   ├── deploy.sh                       # 部署管理脚本
│   ├── start.sh                        # 容器启动脚本
│   └── ...
├── scripts/                            # 启动脚本
└── docs/                               # 文档
    ├── Docker容器化部署指南.md
    └── 项目结构说明.md
```

## 🔧 高级功能

### 数据库迁移

```bash
# 查看迁移状态
python database/tools/db_manager.py migration-status

# 创建新迁移
python database/tools/create_migration.py create add_new_field --database client

# 执行迁移
python database/tools/db_manager.py migrate
```

### Docker 管理

```bash
# 查看服务状态
./docker/deploy.sh status

# 查看日志
./docker/deploy.sh logs

# 备份数据
./docker/deploy.sh backup

# 更新服务
./docker/deploy.sh update
```

### 工作流配置

系统通过配置文件管理工作流参数映射：

```yaml
task_types:
  text_to_image:
    workflows:
      sd_basic:
        workflow_file: "workflows/text_to_image/文生图.json"
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

### Docker 环境问题

1. **容器启动失败**
   ```bash
   # 查看容器日志
   ./docker/deploy.sh logs

   # 检查服务状态
   ./docker/deploy.sh status
   ```

2. **数据库连接失败**
   ```bash
   # 检查数据库容器状态
   docker-compose ps mysql

   # 查看数据库日志
   docker-compose logs mysql
   ```

3. **端口冲突**
   ```bash
   # 修改 .env 文件中的端口配置
   FASTAPI_PORT=8080
   CLIENT_PORT=8081
   ADMIN_PORT=8082
   ```

### 传统部署问题

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
   ```bash
   # 检查数据库状态
   python database/tools/db_manager.py status

   # 运行迁移
   python database/tools/db_manager.py migrate
   ```

5. **认证失败**
   - 检查token是否过期
   - 验证client_id和client_secret
   - 确认请求头格式正确

### 性能优化

- 调整 Celery Worker 数量
- 配置 Redis 内存限制
- 优化工作流参数
- 使用 Docker 资源限制

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
