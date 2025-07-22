#!/bin/bash

# ComfyUI Web Service Docker 部署脚本
# 作者: ComfyUI Web Service Team
# 用途: 自动化部署 ComfyUI Web Service 到 Docker 环境

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"

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

# 显示帮助信息
show_help() {
    cat << EOF
ComfyUI Web Service Docker 部署脚本

用法: $0 [选项] [命令]

命令:
    build       构建 Docker 镜像
    start       启动服务
    stop        停止服务
    restart     重启服务
    logs        查看日志
    status      查看服务状态
    clean       清理未使用的资源
    backup      备份数据
    restore     恢复数据
    update      更新服务
    migrate     运行数据库迁移
    db-status   查看数据库状态

选项:
    -e, --env FILE      指定环境文件 (默认: .env)
    -f, --file FILE     指定 compose 文件 (默认: docker-compose.yml)
    -p, --prod          使用生产环境配置
    -d, --detach        后台运行
    -h, --help          显示此帮助信息

示例:
    $0 build                    # 构建镜像
    $0 start -d                 # 后台启动服务
    $0 -p start                 # 使用生产配置启动
    $0 logs comfyui-web         # 查看特定服务日志
    $0 backup /path/to/backup   # 备份到指定目录

EOF
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    # 检查 Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    
    # 检查 Docker 服务状态
    if ! docker info &> /dev/null; then
        log_error "Docker 服务未运行，请启动 Docker 服务"
        exit 1
    fi
    
    log_info "依赖检查通过"
}

# 检查环境文件
check_env_file() {
    local env_file="$SCRIPT_DIR/$ENV_FILE"
    
    if [ ! -f "$env_file" ]; then
        log_warn "环境文件 $env_file 不存在，创建默认配置..."
        cp "$SCRIPT_DIR/.env" "$env_file"
        log_info "请编辑 $env_file 文件配置您的环境变量"
        return 1
    fi
    
    log_info "环境文件检查通过: $env_file"
    return 0
}

# 构建镜像
build_image() {
    log_info "构建 Docker 镜像..."
    
    cd "$SCRIPT_DIR"
    
    # 构建镜像
    docker-compose -f "$COMPOSE_FILE" build --no-cache
    
    if [ $? -eq 0 ]; then
        log_info "镜像构建成功"
    else
        log_error "镜像构建失败"
        exit 1
    fi
}

# 启动服务
start_services() {
    local detach_flag=""
    
    if [ "$DETACH" = "true" ]; then
        detach_flag="-d"
    fi
    
    log_info "启动服务..."
    
    cd "$SCRIPT_DIR"
    
    # 启动服务
    docker-compose -f "$COMPOSE_FILE" up $detach_flag
    
    if [ $? -eq 0 ]; then
        log_info "服务启动成功"
        
        if [ "$DETACH" = "true" ]; then
            log_info "服务正在后台运行"
            show_service_info
        fi
    else
        log_error "服务启动失败"
        exit 1
    fi
}

# 停止服务
stop_services() {
    log_info "停止服务..."
    
    cd "$SCRIPT_DIR"
    
    docker-compose -f "$COMPOSE_FILE" down
    
    if [ $? -eq 0 ]; then
        log_info "服务停止成功"
    else
        log_error "服务停止失败"
        exit 1
    fi
}

# 重启服务
restart_services() {
    log_info "重启服务..."
    
    stop_services
    sleep 5
    start_services
}

# 查看日志
show_logs() {
    local service="$1"
    
    cd "$SCRIPT_DIR"
    
    if [ -n "$service" ]; then
        log_info "查看服务 $service 的日志..."
        docker-compose -f "$COMPOSE_FILE" logs -f "$service"
    else
        log_info "查看所有服务日志..."
        docker-compose -f "$COMPOSE_FILE" logs -f
    fi
}

# 查看服务状态
show_status() {
    log_info "服务状态:"
    
    cd "$SCRIPT_DIR"
    
    docker-compose -f "$COMPOSE_FILE" ps
    
    echo ""
    log_info "资源使用情况:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
}

# 清理资源
clean_resources() {
    log_info "清理未使用的 Docker 资源..."
    
    # 清理未使用的镜像
    docker image prune -f
    
    # 清理未使用的容器
    docker container prune -f
    
    # 清理未使用的网络
    docker network prune -f
    
    # 清理未使用的数据卷 (谨慎使用)
    read -p "是否清理未使用的数据卷? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker volume prune -f
    fi
    
    log_info "资源清理完成"
}

# 备份数据
backup_data() {
    local backup_dir="$1"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    
    if [ -z "$backup_dir" ]; then
        backup_dir="./backups/backup_$timestamp"
    fi
    
    log_info "备份数据到: $backup_dir"
    
    mkdir -p "$backup_dir"
    
    cd "$SCRIPT_DIR"
    
    # 备份数据卷
    log_info "备份 MySQL 数据..."
    docker run --rm -v comfyui-web-service_mysql_data:/data -v "$backup_dir":/backup alpine tar czf /backup/mysql_data.tar.gz -C /data .
    
    log_info "备份 Redis 数据..."
    docker run --rm -v comfyui-web-service_redis_data:/data -v "$backup_dir":/backup alpine tar czf /backup/redis_data.tar.gz -C /data .
    
    log_info "备份应用日志..."
    docker run --rm -v comfyui-web-service_comfyui_logs:/data -v "$backup_dir":/backup alpine tar czf /backup/app_logs.tar.gz -C /data .
    
    # 备份配置文件
    log_info "备份配置文件..."
    cp -r "$SCRIPT_DIR" "$backup_dir/docker_config"
    cp "$PROJECT_ROOT/backend/config.yaml" "$backup_dir/"
    
    log_info "备份完成: $backup_dir"
}

# 恢复数据
restore_data() {
    local backup_dir="$1"
    
    if [ -z "$backup_dir" ] || [ ! -d "$backup_dir" ]; then
        log_error "请指定有效的备份目录"
        exit 1
    fi
    
    log_info "从备份恢复数据: $backup_dir"
    
    # 停止服务
    stop_services
    
    # 恢复数据卷
    if [ -f "$backup_dir/mysql_data.tar.gz" ]; then
        log_info "恢复 MySQL 数据..."
        docker run --rm -v comfyui-web-service_mysql_data:/data -v "$backup_dir":/backup alpine tar xzf /backup/mysql_data.tar.gz -C /data
    fi
    
    if [ -f "$backup_dir/redis_data.tar.gz" ]; then
        log_info "恢复 Redis 数据..."
        docker run --rm -v comfyui-web-service_redis_data:/data -v "$backup_dir":/backup alpine tar xzf /backup/redis_data.tar.gz -C /data
    fi
    
    if [ -f "$backup_dir/app_logs.tar.gz" ]; then
        log_info "恢复应用日志..."
        docker run --rm -v comfyui-web-service_comfyui_logs:/data -v "$backup_dir":/backup alpine tar xzf /backup/app_logs.tar.gz -C /data
    fi
    
    log_info "数据恢复完成"
}

# 更新服务
update_services() {
    log_info "更新服务..."

    # 拉取最新代码 (如果是 git 仓库)
    if [ -d "$PROJECT_ROOT/.git" ]; then
        log_info "拉取最新代码..."
        cd "$PROJECT_ROOT"
        git pull
    fi

    # 重新构建镜像
    build_image

    # 重启服务
    restart_services

    log_info "服务更新完成"
}

# 运行数据库迁移
run_database_migration() {
    log_info "运行数据库迁移..."

    cd "$SCRIPT_DIR"

    # 检查服务是否运行
    if ! docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        log_error "服务未运行，请先启动服务"
        exit 1
    fi

    # 在容器中运行迁移
    docker-compose -f "$COMPOSE_FILE" exec comfyui-web python database/tools/db_manager.py migrate

    if [ $? -eq 0 ]; then
        log_info "数据库迁移完成"
    else
        log_error "数据库迁移失败"
        exit 1
    fi
}

# 查看数据库状态
show_database_status() {
    log_info "查看数据库状态..."

    cd "$SCRIPT_DIR"

    # 检查服务是否运行
    if ! docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        log_error "服务未运行，请先启动服务"
        exit 1
    fi

    # 在容器中查看数据库状态
    docker-compose -f "$COMPOSE_FILE" exec comfyui-web python database/tools/db_manager.py status

    echo ""
    log_info "迁移状态:"
    docker-compose -f "$COMPOSE_FILE" exec comfyui-web python database/tools/db_manager.py migration-status
}

# 显示服务信息
show_service_info() {
    cat << EOF

=== ComfyUI Web Service 服务信息 ===

FastAPI 主服务:    http://localhost:8000
客户端服务:        http://localhost:8001  
管理后台服务:      http://localhost:8002
API 文档:          http://localhost:8000/docs

使用以下命令管理服务:
  查看状态:   $0 status
  查看日志:   $0 logs
  停止服务:   $0 stop
  重启服务:   $0 restart

EOF
}

# 解析命令行参数
DETACH="false"
PRODUCTION="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--env)
            ENV_FILE="$2"
            shift 2
            ;;
        -f|--file)
            COMPOSE_FILE="$2"
            shift 2
            ;;
        -p|--prod)
            PRODUCTION="true"
            COMPOSE_FILE="docker-compose.prod.yml"
            shift
            ;;
        -d|--detach)
            DETACH="true"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        build|start|stop|restart|logs|status|clean|backup|restore|update|migrate|db-status)
            COMMAND="$1"
            shift
            break
            ;;
        *)
            log_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

# 主执行逻辑
main() {
    log_info "=== ComfyUI Web Service Docker 部署脚本 ==="
    
    # 检查依赖
    check_dependencies
    
    # 检查环境文件
    if ! check_env_file; then
        exit 1
    fi
    
    # 执行命令
    case "$COMMAND" in
        build)
            build_image
            ;;
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        logs)
            show_logs "$1"
            ;;
        status)
            show_status
            ;;
        clean)
            clean_resources
            ;;
        backup)
            backup_data "$1"
            ;;
        restore)
            restore_data "$1"
            ;;
        update)
            update_services
            ;;
        migrate)
            run_database_migration
            ;;
        db-status)
            show_database_status
            ;;
        *)
            log_error "请指定命令: build, start, stop, restart, logs, status, clean, backup, restore, update, migrate, db-status"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
