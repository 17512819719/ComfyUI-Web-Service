# ComfyUI Web Service

这是一个基于FastAPI和Celery的ComfyUI分布式服务，提供文生图和图生视频的API接口。

## 功能特性

- 🎨 文生图API接口
- 🎬 图生视频API接口
- 🔄 异步任务处理
- 📊 任务进度监控
- 🌐 分布式节点支持
- 🚀 自动服务管理
- ⚡ 高性能Redis缓存
- 📝 完整的API文档

## 系统要求

- Python 3.8+
- Redis
- ComfyUI（需要单独安装和运行）
- 足够的GPU内存用于AI模型推理

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置ComfyUI

在 `config.yaml` 中配置ComfyUI的安装路径：

```yaml
# ComfyUI配置
comfyui:
  # ComfyUI安装路径，支持多个路径，按优先级查找
  paths:
    - "E:\\ComfyUI\\ComfyUI\\python.exe"  # 默认路径
    - "C:\\ComfyUI\\ComfyUI\\python.exe"
    - "D:\\ComfyUI\\ComfyUI\\python.exe"
  # ComfyUI服务端口
  port: 8188
  # ComfyUI输出目录
  output_dir: "E:\\ComfyUI\\ComfyUI\\output"
```

### 3. 启动ComfyUI服务

**重要**: 请先手动启动ComfyUI服务，然后再启动其他服务。

```bash
# 进入ComfyUI安装目录
cd E:\ComfyUI\ComfyUI

# 启动ComfyUI服务
python main.py --listen 0.0.0.0 --port 8188
```

### 4. 启动其他服务

#### 方式一：使用标准启动脚本

```bash
python start_services.py
```

#### 方式二：使用改进版启动脚本（推荐）

```bash
python start_services_improved.py
```

启动脚本会自动：
- 检测并启动Redis服务
- 检测ComfyUI服务是否运行（如果未运行会提示并退出）
- 启动Celery Worker
- 启动FastAPI服务

### 5. 停止服务

```bash
python stop_services.py
```

**注意**: 此脚本只会停止Redis、Celery Worker和FastAPI服务，ComfyUI服务需要手动停止。

### 6. 检查服务状态

```bash
python test_services.py
```

## 服务说明

### 启动的服务

1. **Redis服务** (端口: 6379)
   - 用于任务队列和缓存
   - 自动检测项目目录下的Redis安装

2. **ComfyUI服务** (端口: 8188，可配置)
   - AI模型推理服务
   - 自动检测ComfyUI安装路径
   - 支持自定义端口配置

3. **Celery Worker** 
   - 异步任务处理
   - 与Redis配合工作

4. **FastAPI服务** (端口: 8000)
   - Web API接口
   - 自动生成API文档

### 服务地址

- FastAPI服务: http://localhost:8000
- API文档: http://localhost:8000/docs
- ComfyUI服务: http://localhost:8188 (可配置)

## 配置说明

### ComfyUI配置

在 `config.yaml` 中可以配置ComfyUI相关设置：

```yaml
comfyui:
  # ComfyUI安装路径列表，按优先级查找
  paths:
    - "E:\\ComfyUI\\ComfyUI\\python.exe"
    - "C:\\ComfyUI\\ComfyUI\\python.exe"
  # ComfyUI服务端口
  port: 8188
  # ComfyUI输出目录
  output_dir: "E:\\ComfyUI\\ComfyUI\\output"
```

### 模型配置

```yaml
text_to_image:
  ckpt_name: realisticVisionV60B1_v51HyperVAE.safetensors
  sampler_name: euler
  scheduler: normal
  default_width: 512
  default_height: 512
  default_steps: 20
  default_cfg_scale: 7.0

image_to_video:
  model_name: realisticVisionV60B1_v51HyperVAE.safetensors
  default_fps: 8
  default_duration: 5.0
  default_motion_strength: 0.8
```

## API使用

### 文生图

```bash
curl -X POST "http://localhost:8000/generate_image" \
     -H "Content-Type: application/json" \
     -d '{
       "prompt": "a beautiful landscape",
       "negative_prompt": "blurry, low quality",
       "width": 512,
       "height": 512
     }'
```

### 图生视频

```bash
curl -X POST "http://localhost:8000/generate_video" \
     -H "Content-Type: application/json" \
     -d '{
       "image_path": "path/to/image.jpg",
       "prompt": "moving landscape",
       "negative_prompt": "static, still"
     }'
```

## 故障排除

### 1. ComfyUI启动失败

**问题**: ComfyUI服务无法启动

**解决方案**:
1. 检查ComfyUI是否正确安装
2. 确保ComfyUI目录下有 `main.py` 文件
3. 手动启动ComfyUI: `python main.py --listen 0.0.0.0 --port 8188`
4. 确保ComfyUI服务正在运行后再启动其他服务

### 2. 启动脚本提示ComfyUI未运行

**问题**: 启动脚本提示"ComfyUI服务未运行"

**解决方案**:
1. 先手动启动ComfyUI服务
2. 确保ComfyUI在正确的端口运行（默认8188）
3. 使用 `python test_services.py` 检查ComfyUI状态
4. 然后再运行启动脚本

### 3. Redis启动失败

**问题**: Redis服务无法启动

**解决方案**:
1. 确保Redis文件夹在项目根目录下
2. 手动启动Redis: `Redis-x64-3.2.100\redis-server.exe`
3. 或者安装Redis到系统PATH中

### 4. ComfyUI连接失败

**问题**: 无法连接到ComfyUI服务

**解决方案**:
1. 确保ComfyUI正在运行并可以访问
2. 检查端口配置是否正确
3. 检查防火墙设置
4. 使用 `python test_services.py` 检查服务状态

### 5. 端口冲突

**问题**: 端口被占用

**解决方案**:
1. 在 `config.yaml` 中修改ComfyUI端口
2. 使用 `python stop_services.py` 停止其他服务
3. 检查是否有其他程序占用端口

### 6. 服务启动顺序

**正确的启动顺序**:
1. 先启动ComfyUI服务
2. 再运行启动脚本启动其他服务（Redis、Celery Worker、FastAPI）

**停止顺序**:
1. 使用停止脚本停止其他服务
2. 手动停止ComfyUI服务

## 开发说明

### 项目结构

## 更新日志

### v1.2.0
- 🔄 修改ComfyUI服务管理方式
- ✨ ComfyUI服务需要手动启动，启动脚本只负责检测
- ✨ 停止脚本不再停止ComfyUI服务
- 📝 更新文档说明新的启动方式
- 🐛 修复服务启动顺序问题

### v1.1.0
- ✨ 新增ComfyUI服务自动检测和启动
- ✨ 新增配置文件支持
- ✨ 改进服务管理脚本
- ✨ 新增服务状态检测功能
- 🐛 修复多个已知问题
- 📝 更新文档

### v1.0.0
- 🎉 初始版本发布
- ✨ 基础文生图和图生视频功能
- ✨ FastAPI + Celery架构
- ✨ Redis缓存支持