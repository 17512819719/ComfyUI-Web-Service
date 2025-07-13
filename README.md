# ComfyUI Web Service

一个基于 FastAPI 和 Celery 的 ComfyUI 分布式 Web 服务系统，支持多种 AI 内容生成任务的统一管理和调度。

## 🌟 特性

- **多模态内容生成**: 支持文生图、SDXL 等多种 AI 生成任务
- **分布式架构**: 基于 Celery 的异步任务队列，支持多节点部署
- **配置驱动**: 通过 YAML 配置文件管理工作流和参数映射
- **RESTful API**: 完整的 REST API 接口，支持任务提交、状态查询、结果获取
- **Web 界面**: 提供美观的 HTML 客户端和 Vue.js 管理后台
- **实时监控**: WebSocket 实时任务进度监控
- **任务管理**: 支持任务优先级、批量处理、状态追踪
- **局域网访问**: 支持局域网内多设备访问

## 🏗️ 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Client    │    │  Vue.js Admin   │    │   Mobile App    │
│   (HTML/JS)     │    │   Dashboard     │    │   (Future)      │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │      FastAPI Server       │
                    │    (REST API + Auth)      │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │     Celery Workers        │
                    │   (Task Processing)       │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │      ComfyUI API          │
                    │   (AI Generation)         │
                    └───────────────────────────┘
```

## 📋 系统要求

### 硬件要求
- **GPU**: NVIDIA GPU (推荐 8GB+ VRAM)
- **内存**: 16GB+ RAM
- **存储**: 50GB+ 可用空间

### 软件要求
- **Python**: 3.8+
- **ComfyUI**: 已安装并配置
- **Redis**: 任务队列服务
- **MySQL**: 数据库 (可选，用于管理后台)

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

### 2. 配置系统

编辑 `backend/config.yaml` 文件：

```yaml
# ComfyUI配置
comfyui:
  host: "127.0.0.1"
  port: 8188
  output_dir: "E:\\ComfyUI\\ComfyUI\\output"  # 修改为你的ComfyUI输出目录

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
        workflow_file: "path/to/your/workflow.json"  # 修改为实际路径
```

### 3. 启动服务

使用一键启动脚本：

```bash
# Windows
start_all.bat

# 或手动启动各服务
python scripts/start_redis.py      # 启动 Redis
python scripts/start_celery.py     # 启动 Celery Worker
python scripts/start_fastapi.py    # 启动 FastAPI 服务
```

### 4. 访问服务

- **Web 客户端**: 打开 `Client/Client-ComfyUI.html`
- **API 文档**: http://localhost:8000/docs
- **管理后台**: http://localhost:8000/admin (需要先构建)

## 📁 项目结构

```
ComfyUI-Web-Service/
├── backend/                    # 后端服务
│   ├── app/                   # FastAPI 应用
│   │   ├── api/              # API 路由和模式
│   │   ├── core/             # 核心业务逻辑
│   │   ├── processors/       # 任务处理器
│   │   └── queue/            # Celery 任务队列
│   ├── workflows/            # ComfyUI 工作流文件
│   ├── config.yaml          # 系统配置文件
│   └── requirements.txt     # Python 依赖
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

## 📡 API 接口

### 文生图接口

```bash
POST /api/v2/tasks/text-to-image
Content-Type: application/json
Authorization: Bearer <token>

{
  "prompt": "a beautiful landscape",
  "negative_prompt": "blurry, low quality",
  "width": 1024,
  "height": 1024,
  "workflow_name": "sd_basic"
}
```

### 任务状态查询

```bash
GET /api/v2/tasks/{task_id}
Authorization: Bearer <token>
```

### 获取可用工作流

```bash
GET /api/v2/workflows
Authorization: Bearer <token>
```

## 🛠️ 开发指南

### 添加新工作流

1. 将 ComfyUI 工作流 JSON 文件放入 `backend/workflows/` 目录
2. 在 `config.yaml` 中添加工作流配置
3. 配置参数映射关系
4. 重启服务

### 自定义任务处理器

```python
# backend/app/processors/custom_processor.py
from ..core.base import BaseTaskProcessor

class CustomTaskProcessor(BaseTaskProcessor):
    def process(self, request_data):
        # 实现自定义处理逻辑
        pass
```

## 🔍 监控和调试

### 检查服务状态

```bash
python scripts/check_status.py
```

### 清理任务队列

```bash
python scripts/cleanup_tasks.py
```

### 查看日志

- FastAPI 日志: 控制台输出
- Celery 日志: Celery Worker 终端
- Redis 日志: Redis 服务日志

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
