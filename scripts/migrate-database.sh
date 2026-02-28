#!/bin/bash
# =============================================================================
# 数据库迁移脚本
# 将数据库从旧架构迁移到新架构
# =============================================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 检查Docker是否运行
check_docker() {
    log_step "检查Docker服务状态..."
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker未运行，请启动Docker服务"
        exit 1
    fi
    log_info "Docker服务运行正常"
}

# 检查TimescaleDB容器
check_db_container() {
    log_step "检查TimescaleDB容器..."
    if ! docker ps --filter "name=timescale" --format "{{.Names}}" | grep -q "timescale"; then
        log_error "TimescaleDB容器未运行，请先启动数据库"
        exit 1
    fi
    log_info "TimescaleDB容器运行正常"
}

# 停止相关服务
stop_services() {
    log_step "停止相关服务..."
    log_warn "正在停止 api-service 和 binance-service..."
    cd /home/ppadmin/code/quant-trading-system/docker
    docker-compose stop api-service binance-service 2>/dev/null || true
    log_info "服务已停止"
}

# 备份数据库
backup_database() {
    log_step "备份数据库..."
    log_warn "正在创建数据库备份..."

    # 创建备份目录
    BACKUP_DIR="/home/ppadmin/code/quant-trading-system/backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"

    # 备份klines_history表
    docker exec -i timescale-db pg_dump -U dbuser -d trading_db -t klines_history --data-only > "$BACKUP_DIR/klines_history.sql"

    if [ -s "$BACKUP_DIR/klines_history.sql" ]; then
        log_info "备份完成: $BACKUP_DIR/klines_history.sql"
    else
        log_error "备份失败或文件为空"
        exit 1
    fi
}

# 执行迁移
run_migration() {
    log_step "执行数据库迁移..."
    log_warn "正在执行迁移脚本，这可能需要几分钟..."

    # 复制迁移脚本到容器
    docker cp /home/ppadmin/code/quant-trading-system/docker/init-scripts/02-migrate-to-unified-architecture.sql timescale-db:/tmp/migrate.sql

    # 执行迁移
    docker exec -i timescale-db psql -U dbuser -d trading_db -f /tmp/migrate.sql

    if [ $? -eq 0 ]; then
        log_info "迁移脚本执行成功"
    else
        log_error "迁移脚本执行失败"
        exit 1
    fi
}

# 验证迁移
verify_migration() {
    log_step "验证迁移结果..."

    # 复制验证脚本到容器
    docker cp /home/ppadmin/code/quant-trading-system/docker/init-scripts/99-verify-migration.sql timescale-db:/tmp/verify.sql

    # 执行验证
    docker exec -i timescale-db psql -U dbuser -d trading_db -f /tmp/verify.sql

    if [ $? -eq 0 ]; then
        log_info "迁移验证成功"
    else
        log_warn "迁移验证完成，但可能有警告信息"
    fi
}

# 重新启动服务
start_services() {
    log_step "重新启动服务..."
    log_info "正在启动 api-service 和 binance-service..."
    docker-compose start api-service binance-service

    # 等待服务启动
    log_info "等待服务启动完成..."
    sleep 5

    # 检查服务状态
    if docker-compose ps api-service binance-service | grep -q "Up"; then
        log_info "服务启动成功"
    else
        log_warn "服务可能未完全启动，请检查日志"
    fi
}

# 显示最终状态
show_status() {
    log_step "显示最终状态..."

    echo ""
    echo "========================================"
    echo "数据库状态:"
    echo "========================================"
    docker exec -i timescale-db psql -U dbuser -d trading_db -c "\dt"

    echo ""
    echo "========================================"
    echo "触发器状态:"
    echo "========================================"
    docker exec -i timescale-db psql -U dbuser -d trading_db -c "\dT" | grep -E "(trigger_|Trigger)"
}

# 显示使用说明
show_usage() {
    cat << EOF
用法: $0 [选项]

选项:
    --stop-only      仅停止服务
    --start-only     仅启动服务
    --verify-only    仅验证迁移
    --help          显示此帮助信息

示例:
    $0              执行完整迁移
    $0 --stop-only  仅停止服务
    $0 --start-only 仅启动服务

EOF
}

# 主函数
main() {
    echo ""
    echo "========================================"
    echo "数据库架构迁移工具"
    echo "从旧架构迁移到统一订阅与实时数据架构"
    echo "========================================"
    echo ""

    # 解析命令行参数
    case "${1:-}" in
        --help)
            show_usage
            exit 0
            ;;
        --stop-only)
            check_docker
            check_db_container
            stop_services
            log_info "服务已停止"
            exit 0
            ;;
        --start-only)
            check_docker
            check_db_container
            start_services
            show_status
            exit 0
            ;;
        --verify-only)
            check_docker
            check_db_container
            verify_migration
            exit 0
            ;;
    esac

    # 执行完整迁移流程
    check_docker
    check_db_container

    log_warn "即将开始数据库迁移，这将:"
    log_warn "1. 停止相关服务"
    log_warn "2. 备份重要数据"
    log_warn "3. 执行迁移脚本"
    log_warn "4. 验证迁移结果"
    log_warn "5. 重新启动服务"
    echo ""

    read -p "是否继续? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "迁移已取消"
        exit 0
    fi

    echo ""
    stop_services
    backup_database
    run_migration
    verify_migration
    start_services
    show_status

    echo ""
    echo "========================================"
    log_info "迁移完成！"
    echo "========================================"
    echo ""
    log_info "下一步:"
    log_info "1. 检查服务日志: docker-compose logs -f api-service"
    log_info "2. 检查服务日志: docker-compose logs -f binance-service"
    log_info "3. 如果遇到问题，可以回滚到备份"
    echo ""
}

# 执行主函数
main "$@"
