#!/bin/bash

# 服务管理脚本

SERVICE_NAME="umeikouagent.service"
PROJECT_DIR="/usr/Project/article_collection_django"

show_usage() {
    echo "用法: $0 {start|stop|restart|status|logs|check}"
    echo ""
    echo "命令说明:"
    echo "  start   - 启动服务"
    echo "  stop    - 停止服务"
    echo "  restart - 重启服务"
    echo "  status  - 查看服务状态"
    echo "  logs    - 查看实时日志"
    echo "  check   - 运行健康检查"
    exit 1
}

case "$1" in
    start)
        echo "🚀 启动服务..."
        systemctl start $SERVICE_NAME
        systemctl start nginx
        sleep 2
        systemctl status $SERVICE_NAME --no-pager
        ;;
    stop)
        echo "🛑 停止服务..."
        systemctl stop $SERVICE_NAME
        systemctl status $SERVICE_NAME --no-pager
        ;;
    restart)
        echo "🔄 重启服务..."
        systemctl restart $SERVICE_NAME
        systemctl reload nginx
        sleep 2
        systemctl status $SERVICE_NAME --no-pager
        ;;
    status)
        echo "📊 服务状态:"
        systemctl status $SERVICE_NAME --no-pager
        echo ""
        systemctl status nginx --no-pager
        ;;
    logs)
        echo "📋 实时日志 (Ctrl+C 退出):"
        journalctl -u $SERVICE_NAME -f
        ;;
    check)
        bash $PROJECT_DIR/check_service.sh
        ;;
    *)
        show_usage
        ;;
esac
