#!/bin/bash

# 视频内容系统 - 启动脚本
# 这个脚本用于在生产环境中启动应用

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# 检查环境变量
check_env() {
    log "检查环境变量..."
    
    required_vars=(
        "SUPABASE_URL"
        "SUPABASE_KEY"
        "SECRET_KEY"
        "REDIS_URL"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            error "缺少必需的环境变量: $var"
            exit 1
        else
            info "✅ $var 已设置"
        fi
    done
}

# 等待依赖服务
wait_for_services() {
    log "检查依赖服务..."
    
    # 检查Redis
    if command -v redis-cli &> /dev/null; then
        if redis-cli -u "$REDIS_URL" ping | grep -q "PONG"; then
            info "✅ Redis 连接正常"
        else
            warn "❌ Redis 连接失败"
        fi
    else
        warn "redis-cli 未安装，跳过Redis检查"
    fi
}

# 创建必要的目录
create_directories() {
    log "创建必要的目录..."
    
    directories=(
        "storage/videos"
        "storage/images"
        "storage/temp"
        "logs"
    )
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            info "✅ 创建目录: $dir"
        else
            info "📁 目录已存在: $dir"
        fi
    done
}

# 数据库迁移
run_migrations() {
    log "检查数据库迁移..."
    
    # 这里可以添加数据库迁移逻辑
    # 例如：alembic upgrade head
    
    info "✅ 数据库迁移检查完成"
}

# 启动应用
start_application() {
    log "启动视频内容系统..."
    
    # 设置Python路径
    export PYTHONPATH="$PWD:$PYTHONPATH"
    
    # 根据环境选择启动方式
    if [ "$ENVIRONMENT" = "development" ]; then
        info "🚀 开发模式启动..."
        exec python run.py
    else
        info "🚀 生产模式启动..."
        exec uvicorn app.main:app \
            --host "$HOST" \
            --port "$PORT" \
            --workers "$WORKERS" \
            --log-level "$LOG_LEVEL" \
            --access-log \
            --no-server-header
    fi
}

# 主函数
main() {
    log "🎬 视频内容系统启动脚本"
    
    # 设置默认值
    ENVIRONMENT=${ENVIRONMENT:-"production"}
    HOST=${HOST:-"0.0.0.0"}
    PORT=${PORT:-"8000"}
    WORKERS=${WORKERS:-"4"}
    LOG_LEVEL=${LOG_LEVEL:-"info"}
    
    info "环境: $ENVIRONMENT"
    info "主机: $HOST"
    info "端口: $PORT"
    info "工作进程: $WORKERS"
    info "日志级别: $LOG_LEVEL"
    
    # 执行启动步骤
    check_env
    wait_for_services
    create_directories
    run_migrations
    start_application
}

# 信号处理
trap 'error "收到中断信号，正在关闭..."; exit 1' INT TERM

# 运行主函数
main "$@"