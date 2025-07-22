# ComfyUI Web Service Docker 容器化部署指南

## 概述

本指南将详细介绍如何将 ComfyUI Web Service 项目打包成 Docker 容器，并在其他主机上部署运行。项目已经准备了完整的 Docker 配置文件，位于 `docker/` 目录中。

## 目录

1. [前置准备](#前置准备)
2. [快速开始](#快速开始)
3. [配置文件说明](#配置文件说明)
4. [部署模式](#部署模式)
5. [数据持久化](#数据持久化)
6. [网络配置](#网络配置)
7. [监控和日志](#监控和日志)
8. [备份和恢复](#备份和恢复)
9. [故障排除](#故障排除)
10. [生产环境部署](#生产环境部署)

## 前置准备

### 1. 安装 Docker

在目标主机上安装 Docker：

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install docker.io docker-compose-plugin
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

**CentOS/RHEL:**
```bash
sudo yum install docker docker-compose-plugin
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

**注意**: 新版Docker已将Docker Compose集成为`docker compose`子命令。部署脚本会自动检测并使用合适的命令：
- 优先使用 `docker compose` (推荐)
- 兼容旧版 `docker-compose`

**Windows:**
下载并安装 Docker Desktop for Windows

### 2. 验证 Docker 安装

```bash
docker --version

# 检查 Docker Compose (新版)
docker compose version

# 或检查旧版
docker-compose --version

# 测试 Docker
docker run hello-world
```

### 3. 项目文件结构

项目已包含完整的 Docker 配置：

```
docker/
├── Dockerfile                 # 主应用镜像定义
├── docker-compose.yml         # 开发环境配置
├── docker-compose.prod.yml    # 生产环境配置
├── .env                       # 环境变量模板
├── start.sh                   # 容器启动脚本
├── wait-for-it.sh            # 服务等待脚本
├── deploy.sh                  # 部署管理脚本
├── logging.yaml               # 日志配置
├── mysql/
│   └── my.cnf                # MySQL 配置
├── redis/
│   └── redis.conf            # Redis 配置
└── nginx/
    └── nginx.conf            # Nginx 配置
```

## 快速开始

### 1. 克隆项目并进入 Docker 目录

```bash
cd ComfyUI-Web-Service/docker
```

### 2. 复制并配置环境变量

```bash
cp .env .env.local
# 编辑 .env.local 文件，修改必要的配置
nano .env.local
```

### 3. 一键部署

```bash
# Linux/macOS: 给部署脚本执行权限
chmod +x deploy.sh

# 构建并启动服务
./deploy.sh build
./deploy.sh start -d

# Windows: 在 Git Bash 或 WSL 中运行
# 或者直接使用 bash 命令
bash deploy.sh build
bash deploy.sh start -d
```

### 4. 验证部署

```bash
# 查看服务状态
./deploy.sh status

# 查看日志
./deploy.sh logs
```

访问服务：
- FastAPI 主服务: http://localhost:8000
- 客户端界面: http://localhost:8001
- 管理后台: http://localhost:8002
- API 文档: http://localhost:8000/docs

## 配置文件说明

### 1. 环境变量配置 (.env)

主要配置项：

```bash
# 端口配置
MYSQL_PORT=3306
REDIS_PORT=6379
FASTAPI_PORT=8000
CLIENT_PORT=8001
ADMIN_PORT=8002

# 数据库配置
MYSQL_ROOT_PASSWORD=123456
MYSQL_CLIENT_DB=comfyui_client
MYSQL_ADMIN_DB=comfyui_admin
MYSQL_SHARED_DB=comfyui_shared

# 应用配置
LOG_LEVEL=INFO
TZ=Asia/Shanghai

# ComfyUI 节点配置
COMFYUI_NODE_HOST=192.168.1.100
COMFYUI_NODE_PORT=8188

# 安全配置
JWT_SECRET_KEY=your-super-secret-jwt-key
ADMIN_DEFAULT_PASSWORD=admin123456
```

### 2. 应用配置 (config.yaml)

需要修改的关键配置：

```yaml
# 数据库连接
mysql:
  client:
    host: mysql  # 容器内服务名
    port: 3306
    password: "123456"
  admin:
    host: mysql
    port: 3306
    password: "123456"
  shared:
    host: mysql
    port: 3306
    password: "123456"

# Redis 连接
redis:
  host: redis  # 容器内服务名
  port: 6379

# ComfyUI 节点配置
nodes:
  static_nodes:
    - node_id: "comfyui-worker-1"
      host: "192.168.1.100"  # 修改为实际 ComfyUI 服务器 IP
      port: 8188
```

### 3. 服务配置文件

- `mysql/my.cnf` - MySQL 性能优化配置
- `redis/redis.conf` - Redis 缓存配置
- `nginx/nginx.conf` - Nginx 反向代理配置
- `logging.yaml` - Python 日志配置

## 部署模式

### 1. 开发环境部署

使用 `docker-compose.yml` 进行开发环境部署：

```bash
cd docker/

# 构建镜像
./deploy.sh build

# 启动服务（前台运行，便于调试）
./deploy.sh start

# 或后台运行
./deploy.sh start -d
```

### 2. 生产环境部署

使用 `docker-compose.prod.yml` 进行生产环境部署：

```bash
cd docker/

# 使用生产配置构建
./deploy.sh -p build

# 启动生产环境服务
./deploy.sh -p start -d

# 查看服务状态
./deploy.sh -p status
```

### 3. 单机部署

如果不使用 Docker Compose，可以单独运行容器：

```bash
# 创建网络
docker network create comfyui-network

# 启动 MySQL
docker run -d \
  --name comfyui-mysql \
  --network comfyui-network \
  -e MYSQL_ROOT_PASSWORD=123456 \
  -p 3306:3306 \
  -v mysql_data:/var/lib/mysql \
  mysql:8.0

# 启动 Redis
docker run -d \
  --name comfyui-redis \
  --network comfyui-network \
  -p 6379:6379 \
  -v redis_data:/data \
  redis:7-alpine

# 启动主应用
docker run -d \
  --name comfyui-web-service \
  --network comfyui-network \
  -p 8000:8000 -p 8001:8001 -p 8002:8002 \
  -v $(pwd)/backend/outputs:/app/backend/outputs \
  -v $(pwd)/backend/uploads:/app/backend/uploads \
  -v $(pwd)/backend/workflows:/app/backend/workflows \
  -e MYSQL_HOST=comfyui-mysql \
  -e REDIS_HOST=comfyui-redis \
  comfyui-web-service:latest
```

## 数据持久化

### 1. 数据卷管理

项目使用 Docker 数据卷持久化重要数据：

```bash
# 查看数据卷
docker volume ls | grep comfyui

# 数据卷说明
mysql_data          # MySQL 数据库文件
redis_data          # Redis 持久化数据
comfyui_logs        # 应用日志文件
comfyui_temp        # 临时文件
```

### 2. 目录映射

重要目录通过 bind mount 映射到宿主机：

```bash
# 映射关系
./backend/outputs   -> /app/backend/outputs    # 生成的图片/视频
./backend/uploads   -> /app/backend/uploads    # 用户上传文件
./backend/workflows -> /app/backend/workflows  # ComfyUI 工作流
./backend/config.yaml -> /app/backend/config.yaml  # 配置文件
```

### 3. 备份策略

使用部署脚本进行数据备份：

```bash
# 备份所有数据到指定目录
./deploy.sh backup /path/to/backup

# 备份内容包括：
# - MySQL 数据库
# - Redis 数据
# - 应用日志
# - 配置文件
# - 用户上传文件
# - 生成的输出文件
```

### 4. 恢复数据

```bash
# 从备份恢复数据
./deploy.sh restore /path/to/backup

# 注意：恢复操作会停止服务并覆盖现有数据
```

## 网络配置

### 1. 端口映射

默认端口配置：

| 服务 | 容器端口 | 宿主机端口 | 说明 |
|------|----------|------------|------|
| FastAPI 主服务 | 8000 | 8000 | API 服务和文档 |
| 客户端服务 | 8001 | 8001 | 客户端 Web 界面 |
| 管理后台服务 | 8002 | 8002 | 管理后台界面 |
| MySQL | 3306 | 3306 | 数据库服务 |
| Redis | 6379 | 6379 | 缓存服务 |
| Nginx | 80/443 | 80/443 | 反向代理 (可选) |

### 2. 防火墙配置

**Ubuntu/Debian:**
```bash
sudo ufw allow 8000:8002/tcp
sudo ufw allow 3306/tcp
sudo ufw allow 6379/tcp
sudo ufw reload
```

**CentOS/RHEL:**
```bash
sudo firewall-cmd --permanent --add-port=8000-8002/tcp
sudo firewall-cmd --permanent --add-port=3306/tcp
sudo firewall-cmd --permanent --add-port=6379/tcp
sudo firewall-cmd --reload
```

### 3. 网络安全

生产环境建议：

```bash
# 只绑定本地接口，通过 Nginx 代理
MYSQL_PORT=127.0.0.1:3306:3306
REDIS_PORT=127.0.0.1:6379:6379
FASTAPI_PORT=127.0.0.1:8000:8000

# 使用 Nginx 反向代理对外提供服务
./deploy.sh -p start --profile with-nginx
```

### 4. 跨主机网络

如果需要跨主机部署：

```bash
# 创建 overlay 网络 (Docker Swarm)
docker network create --driver overlay comfyui-overlay

# 或使用外部网络解决方案如 Consul、etcd
```

## 监控和日志

### 1. 日志管理

查看服务日志：

```bash
# 查看所有服务日志
./deploy.sh logs

# 查看特定服务日志
./deploy.sh logs comfyui-web
./deploy.sh logs mysql
./deploy.sh logs redis

# 实时跟踪日志
docker-compose logs -f --tail=100

# 查看容器内日志文件
docker exec -it comfyui-web-service tail -f /app/logs/app.log
```

### 2. 性能监控

使用部署脚本查看资源使用：

```bash
# 查看服务状态和资源使用
./deploy.sh status

# 详细的容器统计信息
docker stats

# 查看容器进程
docker exec -it comfyui-web-service ps aux
```

### 3. 健康检查

所有服务都配置了健康检查：

```bash
# 查看健康状态
docker-compose ps

# 手动健康检查
curl http://localhost:8000/health
curl http://localhost:8001/
curl http://localhost:8002/
```

### 4. 监控集成 (可选)

启用 Prometheus 监控：

```bash
# 启动监控服务
docker-compose --profile monitoring up -d

# 访问 Prometheus
http://localhost:9090
```

## 备份和恢复

### 1. 自动备份

使用部署脚本进行定期备份：

```bash
# 创建备份
./deploy.sh backup

# 备份到指定目录
./deploy.sh backup /opt/backups/$(date +%Y%m%d)

# 设置定时备份 (crontab)
0 2 * * * cd /path/to/docker && ./deploy.sh backup /opt/backups/$(date +\%Y\%m\%d)
```

### 2. 手动备份

```bash
# 停止服务
./deploy.sh stop

# 备份数据卷
docker run --rm \
  -v comfyui-web-service_mysql_data:/source \
  -v /backup:/backup \
  alpine tar czf /backup/mysql-$(date +%Y%m%d).tar.gz -C /source .

docker run --rm \
  -v comfyui-web-service_redis_data:/source \
  -v /backup:/backup \
  alpine tar czf /backup/redis-$(date +%Y%m%d).tar.gz -C /source .

# 备份配置和代码
tar czf /backup/config-$(date +%Y%m%d).tar.gz docker/ backend/config.yaml

# 重启服务
./deploy.sh start -d
```

### 3. 数据恢复

```bash
# 使用部署脚本恢复
./deploy.sh restore /path/to/backup

# 手动恢复数据卷
docker run --rm \
  -v comfyui-web-service_mysql_data:/target \
  -v /backup:/backup \
  alpine tar xzf /backup/mysql-20240101.tar.gz -C /target
```

### 4. 迁移到新主机

```bash
# 在源主机上
./deploy.sh backup /tmp/migration
tar czf comfyui-migration.tar.gz /tmp/migration docker/ backend/

# 传输到目标主机
scp comfyui-migration.tar.gz user@target-host:/tmp/

# 在目标主机上
tar xzf /tmp/comfyui-migration.tar.gz
cd docker/
./deploy.sh restore /tmp/migration
./deploy.sh start -d
```

## 故障排除

### 1. 常见问题

**容器启动失败：**
```bash
# 查看容器日志
./deploy.sh logs comfyui-web

# 查看详细启动日志
docker-compose logs --no-color comfyui-web

# 进入容器调试
docker exec -it comfyui-web-service /bin/bash
```

**数据库连接失败：**
```bash
# 检查数据库容器状态
./deploy.sh status

# 测试数据库连接
docker exec -it comfyui-mysql mysql -u root -p123456

# 检查数据库初始化
docker exec -it comfyui-mysql mysql -u root -p123456 -e "SHOW DATABASES;"
```

**端口冲突：**
```bash
# 查看端口占用
netstat -tlnp | grep :8000
# 或
ss -tlnp | grep :8000

# 修改 .env 文件中的端口配置
FASTAPI_PORT=8080
CLIENT_PORT=8081
ADMIN_PORT=8082
```

**服务无响应：**
```bash
# 检查服务健康状态
curl -f http://localhost:8000/health

# 重启特定服务
docker-compose restart comfyui-web

# 查看资源使用情况
docker stats
```

**权限问题：**
```bash
# 检查文件权限
ls -la backend/outputs backend/uploads

# 修复权限
sudo chown -R $USER:$USER backend/outputs backend/uploads
chmod -R 755 backend/outputs backend/uploads
```

### 2. 性能优化

**调整资源限制：**
```bash
# 编辑 .env 文件
APP_MEMORY_LIMIT=8G
APP_CPU_LIMIT=4.0
MYSQL_MEMORY_LIMIT=2G
REDIS_MEMORY_LIMIT=1G
```

**优化数据库性能：**
```bash
# 编辑 mysql/my.cnf
innodb_buffer_pool_size=1G
max_connections=500
query_cache_size=64M
```

**清理系统资源：**
```bash
# 清理 Docker 资源
./deploy.sh clean

# 清理日志文件
docker exec -it comfyui-web-service find /app/logs -name "*.log" -mtime +7 -delete
```

## 生产环境部署

### 1. 生产环境配置

使用生产环境配置文件：

```bash
# 复制生产环境配置
cp docker-compose.prod.yml docker-compose.yml
cp .env .env.prod

# 编辑生产环境变量
nano .env.prod
```

关键生产环境配置：

```bash
# 安全配置
MYSQL_ROOT_PASSWORD=your-strong-password
REDIS_PASSWORD=your-redis-password
JWT_SECRET_KEY=your-super-secret-jwt-key

# 性能配置
APP_MEMORY_LIMIT=8G
APP_CPU_LIMIT=4.0
MYSQL_MEMORY_LIMIT=2G

# 网络安全
MYSQL_PORT=127.0.0.1:3306:3306
REDIS_PORT=127.0.0.1:6379:6379
```

### 2. SSL/HTTPS 配置

```bash
# 生成 SSL 证书
mkdir -p docker/nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout docker/nginx/ssl/key.pem \
  -out docker/nginx/ssl/cert.pem

# 启用 HTTPS
./deploy.sh -p start --profile with-nginx
```

### 3. 监控和告警

```bash
# 启用完整监控
./deploy.sh -p start --profile monitoring --profile logging

# 配置告警 (需要额外配置)
# - Prometheus + Grafana 监控
# - ELK 日志分析
# - 邮件/短信告警
```

### 4. 高可用部署

```bash
# Docker Swarm 集群部署
docker swarm init
docker stack deploy -c docker-compose.swarm.yml comfyui

# 或使用 Kubernetes
kubectl apply -f k8s/
```

## 部署检查清单

### 部署前检查
- [ ] Docker 和 Docker Compose 已安装并测试
- [ ] 项目文件完整，包含所有必要的配置
- [ ] 环境变量文件已配置 (.env)
- [ ] ComfyUI 节点地址已正确配置
- [ ] 防火墙端口已开放
- [ ] 数据存储目录已准备
- [ ] SSL 证书已配置 (生产环境)

### 部署后验证
- [ ] 所有容器正常启动 (`./deploy.sh status`)
- [ ] 数据库连接正常
- [ ] Redis 缓存工作正常
- [ ] FastAPI 服务可访问 (http://localhost:8000/health)
- [ ] 客户端界面可访问 (http://localhost:8001)
- [ ] 管理后台可访问 (http://localhost:8002)
- [ ] 任务队列工作正常 (Celery)
- [ ] 文件上传下载功能正常
- [ ] ComfyUI 节点连接正常

### 运维检查
- [ ] 日志轮转配置正确
- [ ] 备份策略已实施
- [ ] 监控告警已配置
- [ ] 性能指标正常
- [ ] 安全配置已加固

## 维护操作

### 1. 日常维护

```bash
# 查看服务状态
./deploy.sh status

# 查看日志
./deploy.sh logs

# 更新服务
./deploy.sh update

# 清理资源
./deploy.sh clean
```

### 2. 定期备份

```bash
# 设置自动备份 (crontab -e)
0 2 * * * cd /opt/comfyui && ./docker/deploy.sh backup /opt/backups/$(date +\%Y\%m\%d)
0 3 * * 0 find /opt/backups -mtime +30 -delete
```

### 3. 性能监控

```bash
# 实时监控
watch -n 5 './deploy.sh status'

# 资源使用趋势
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" --no-stream
```

### 4. 故障恢复

```bash
# 快速重启
./deploy.sh restart

# 从备份恢复
./deploy.sh restore /path/to/backup

# 回滚到上一版本
git checkout previous-version
./deploy.sh update
```

---

## 总结

通过本指南，您可以：

1. **快速部署** - 使用一键部署脚本快速启动服务
2. **灵活配置** - 支持开发和生产环境不同配置
3. **数据安全** - 完整的备份恢复机制
4. **易于维护** - 丰富的运维工具和监控手段
5. **高可用性** - 支持集群和负载均衡部署

ComfyUI Web Service 现在可以轻松地在任何支持 Docker 的环境中部署和运行。
