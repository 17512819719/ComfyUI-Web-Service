#!/bin/bash

# ComfyUI Web Service 容器启动脚本
# 作者: ComfyUI Web Service Team
# 描述: 启动所有必要的服务组件

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# 等待服务函数
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local timeout=${4:-60}
    
    log_info "等待 $service_name 服务启动 ($host:$port)..."
    
    local count=0
    while ! nc -z "$host" "$port"; do
        if [ $count -ge $timeout ]; then
            log_error "$service_name 服务启动超时"
            exit 1
        fi
        sleep 1
        count=$((count + 1))
    done
    
    log_info "$service_name 服务已启动"
}

# 检查环境变量
check_environment() {
    log_info "检查环境变量..."
    
    # 设置默认值
    export MYSQL_HOST=${MYSQL_HOST:-mysql}
    export MYSQL_PORT=${MYSQL_PORT:-3306}
    export REDIS_HOST=${REDIS_HOST:-redis}
    export REDIS_PORT=${REDIS_PORT:-6379}
    export LOG_LEVEL=${LOG_LEVEL:-INFO}
    
    log_info "MySQL: $MYSQL_HOST:$MYSQL_PORT"
    log_info "Redis: $REDIS_HOST:$REDIS_PORT"
    log_info "日志级别: $LOG_LEVEL"
}

# 等待依赖服务
wait_for_dependencies() {
    log_info "等待依赖服务启动..."
    
    # 等待 MySQL
    wait_for_service "$MYSQL_HOST" "$MYSQL_PORT" "MySQL" 120
    
    # 等待 Redis
    wait_for_service "$REDIS_HOST" "$REDIS_PORT" "Redis" 60
    
    # 额外等待确保服务完全就绪
    log_info "等待服务完全就绪..."
    sleep 10
}

# 初始化数据库
initialize_database() {
    log_info "初始化数据库..."

    cd /app/backend

    # 检查数据库连接
    python -c "
import sys
sys.path.append('/app/backend')
from app.database.connection import get_mysql_engine
try:
    engine = get_mysql_engine('client')
    with engine.connect() as conn:
        conn.execute('SELECT 1')
    print('数据库连接成功')
except Exception as e:
    print(f'数据库连接失败: {e}')
    sys.exit(1)
"

    if [ $? -eq 0 ]; then
        log_info "数据库连接验证成功"

        # 运行数据库初始化和迁移
        if [ -f "/app/database/tools/db_manager.py" ]; then
            log_info "运行数据库初始化..."
            python /app/database/tools/db_manager.py init

            if [ $? -eq 0 ]; then
                log_info "数据库初始化完成"
            else
                log_warn "数据库初始化可能已完成或部分失败"
            fi
        fi
    else
        log_error "数据库连接失败，退出启动"
        exit 1
    fi
}

# 清理任务队列
cleanup_task_queue() {
    log_info "清理任务队列..."
    
    cd /app/backend
    
    # 清理 Redis 中的任务队列
    python -c "
import redis
import sys
try:
    r = redis.Redis(host='$REDIS_HOST', port=$REDIS_PORT, db=0)
    r.ping()
    
    # 清理任务队列
    keys = r.keys('celery-task-meta-*')
    if keys:
        r.delete(*keys)
        print(f'清理了 {len(keys)} 个任务记录')
    
    # 清理队列
    queues = ['text_to_image', 'image_to_video', 'celery']
    for queue in queues:
        length = r.llen(queue)
        if length > 0:
            r.delete(queue)
            print(f'清理队列 {queue}: {length} 个任务')
            
    print('任务队列清理完成')
except Exception as e:
    print(f'任务队列清理失败: {e}')
    sys.exit(1)
"
}

# 启动 Celery Worker
start_celery() {
    log_info "启动 Celery Worker..."
    
    cd /app/backend
    
    # 启动 Celery Worker (后台运行)
    celery -A app.queue.celery_app worker \
        --loglevel=$LOG_LEVEL \
        --concurrency=4 \
        --max-tasks-per-child=100 \
        --time-limit=3600 \
        --soft-time-limit=3300 \
        --pidfile=/app/temp/celery.pid \
        --logfile=/app/logs/celery.log \
        --detach
    
    if [ $? -eq 0 ]; then
        log_info "Celery Worker 启动成功"
    else
        log_error "Celery Worker 启动失败"
        exit 1
    fi
}

# 启动 FastAPI 主服务
start_fastapi() {
    log_info "启动 FastAPI 主服务..."
    
    cd /app/backend
    
    # 启动 FastAPI (后台运行)
    uvicorn app.main_v2:app \
        --host 0.0.0.0 \
        --port 8000 \
        --log-level $(echo $LOG_LEVEL | tr '[:upper:]' '[:lower:]') \
        --access-log \
        --log-config /app/docker/logging.yaml &
    
    FASTAPI_PID=$!
    echo $FASTAPI_PID > /app/temp/fastapi.pid
    
    log_info "FastAPI 主服务启动中 (PID: $FASTAPI_PID)"
}

# 启动客户端服务
start_client_service() {
    log_info "启动客户端服务..."
    
    cd /app/scripts
    
    # 启动客户端服务 (后台运行)
    python start_client.py &
    
    CLIENT_PID=$!
    echo $CLIENT_PID > /app/temp/client.pid
    
    log_info "客户端服务启动中 (PID: $CLIENT_PID)"
}

# 启动管理后台服务
start_admin_service() {
    log_info "启动管理后台服务..."
    
    cd /app/scripts
    
    # 启动管理后台服务 (后台运行)
    python start_admin.py &
    
    ADMIN_PID=$!
    echo $ADMIN_PID > /app/temp/admin.pid
    
    log_info "管理后台服务启动中 (PID: $ADMIN_PID)"
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    # 检查 FastAPI 服务
    for i in {1..30}; do
        if curl -f http://localhost:8000/health >/dev/null 2>&1; then
            log_info "FastAPI 服务健康检查通过"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "FastAPI 服务健康检查失败"
            exit 1
        fi
        sleep 2
    done
    
    # 检查客户端服务
    for i in {1..30}; do
        if curl -f http://localhost:8001/ >/dev/null 2>&1; then
            log_info "客户端服务健康检查通过"
            break
        fi
        if [ $i -eq 30 ]; then
            log_warn "客户端服务健康检查失败"
        fi
        sleep 2
    done
    
    # 检查管理后台服务
    for i in {1..30}; do
        if curl -f http://localhost:8002/ >/dev/null 2>&1; then
            log_info "管理后台服务健康检查通过"
            break
        fi
        if [ $i -eq 30 ]; then
            log_warn "管理后台服务健康检查失败"
        fi
        sleep 2
    done
}

# 信号处理函数
cleanup() {
    log_info "接收到停止信号，正在关闭服务..."
    
    # 停止所有后台进程
    if [ -f /app/temp/fastapi.pid ]; then
        kill $(cat /app/temp/fastapi.pid) 2>/dev/null || true
    fi
    
    if [ -f /app/temp/client.pid ]; then
        kill $(cat /app/temp/client.pid) 2>/dev/null || true
    fi
    
    if [ -f /app/temp/admin.pid ]; then
        kill $(cat /app/temp/admin.pid) 2>/dev/null || true
    fi
    
    if [ -f /app/temp/celery.pid ]; then
        kill $(cat /app/temp/celery.pid) 2>/dev/null || true
    fi
    
    log_info "服务已停止"
    exit 0
}

# 设置信号处理
trap cleanup SIGTERM SIGINT

# 主启动流程
main() {
    log_info "=== ComfyUI Web Service 容器启动 ==="
    
    # 1. 检查环境
    check_environment
    
    # 2. 等待依赖服务
    wait_for_dependencies
    
    # 3. 初始化数据库
    initialize_database
    
    # 4. 清理任务队列
    cleanup_task_queue
    
    # 5. 启动服务
    start_celery
    sleep 5
    
    start_fastapi
    sleep 5
    
    start_client_service
    sleep 5
    
    start_admin_service
    sleep 5
    
    # 6. 健康检查
    health_check
    
    log_info "=== 所有服务启动完成 ==="
    log_info "FastAPI 主服务: http://localhost:8000"
    log_info "客户端服务: http://localhost:8001"
    log_info "管理后台服务: http://localhost:8002"
    
    # 保持容器运行
    while true; do
        sleep 30
        
        # 检查关键进程是否还在运行
        if ! kill -0 $(cat /app/temp/fastapi.pid 2>/dev/null) 2>/dev/null; then
            log_error "FastAPI 服务异常退出"
            exit 1
        fi
        
        if ! pgrep -f "celery.*worker" >/dev/null; then
            log_error "Celery Worker 异常退出"
            exit 1
        fi
    done
}

# 执行主函数
main "$@"
