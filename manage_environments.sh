#!/bin/bash

# 环境管理脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

show_help() {
    echo "🔧 Umeikou 的阅读分享 - 环境管理工具"
    echo "======================================="
    echo ""
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  dev         启动开发环境 (测试环境)"
    echo "  prod        启动生产环境"
    echo "  deploy      部署到生产环境"
    echo "  status      查看服务状态"
    echo "  logs        查看日志"
    echo "  stop        停止服务"
    echo "  restart     重启服务"
    echo "  backup      备份数据"
    echo "  help        显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 dev      # 启动开发环境"
    echo "  $0 deploy   # 部署到生产环境"
    echo "  $0 status   # 查看服务状态"
}

start_dev() {
    echo "🧪 启动开发环境 (测试环境)"
    echo "========================="
    
    export DJANGO_SETTINGS_MODULE=article_collection_django.settings
    
    echo "📦 检查依赖..."
    pip3 install -r requirements.txt
    
    echo "🗄️  数据库迁移..."
    python3 manage.py migrate
    
    echo "📁 收集静态文件..."
    python3 manage.py collectstatic --noinput
    
    echo "🚀 启动开发服务器..."
    echo "访问地址: http://localhost:8000/"
    python3 manage.py runserver 0.0.0.0:8000
}

start_prod() {
    echo "🏭 启动生产环境"
    echo "==============="
    
    if [ "$EUID" -ne 0 ]; then
        echo "❌ 生产环境需要root权限"
        echo "请使用: sudo $0 prod"
        exit 1
    fi
    
    systemctl start umeikouagent.service
    systemctl start nginx
    
    echo "✅ 生产环境已启动"
    echo "🌐 访问地址: http://umeikouagent.top"
}

deploy_prod() {
    echo "🚀 部署到生产环境"
    echo "=================="
    
    if [ "$EUID" -ne 0 ]; then
        echo "❌ 部署需要root权限"
        echo "请使用: sudo $0 deploy"
        exit 1
    fi
    
    # 检测系统类型
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        if [[ "$ID_LIKE" == *"rhel"* ]] || [[ "$ID_LIKE" == *"centos"* ]] || [[ "$ID" == "alinux" ]]; then
            echo "🔍 检测到 CentOS/RHEL/Alibaba Cloud Linux 系统"
            bash deploy_production_centos.sh
        elif [[ "$ID_LIKE" == *"debian"* ]] || [[ "$ID" == "ubuntu" ]]; then
            echo "🔍 检测到 Ubuntu/Debian 系统"
            bash deploy_production.sh
        else
            echo "⚠️  未知系统类型，使用默认部署脚本"
            bash deploy_production.sh
        fi
    else
        echo "⚠️  无法检测系统类型，使用默认部署脚本"
        bash deploy_production.sh
    fi
}

show_status() {
    echo "📊 服务状态检查"
    echo "==============="
    
    echo "🧪 开发环境:"
    if pgrep -f "manage.py runserver" > /dev/null; then
        echo "  ✅ 开发服务器运行中"
    else
        echo "  ❌ 开发服务器未运行"
    fi
    
    echo ""
    echo "🏭 生产环境:"
    if systemctl is-active --quiet umeikouagent.service; then
        echo "  ✅ Django应用运行中"
    else
        echo "  ❌ Django应用未运行"
    fi
    
    if systemctl is-active --quiet nginx; then
        echo "  ✅ Nginx运行中"
    else
        echo "  ❌ Nginx未运行"
    fi
    
    if systemctl is-active --quiet weekly-digest.timer; then
        echo "  ✅ 定时任务运行中"
    else
        echo "  ❌ 定时任务未运行"
    fi
}

show_logs() {
    echo "📋 查看日志"
    echo "==========="
    
    echo "选择要查看的日志:"
    echo "1) 开发环境日志"
    echo "2) 生产环境应用日志"
    echo "3) Nginx访问日志"
    echo "4) Nginx错误日志"
    echo "5) 系统服务日志"
    
    read -p "请选择 (1-5): " choice
    
    case $choice in
        1)
            echo "开发环境日志 (实时):"
            tail -f logs/django.log 2>/dev/null || echo "日志文件不存在"
            ;;
        2)
            echo "生产环境应用日志:"
            tail -f logs/access.log logs/error.log 2>/dev/null || echo "日志文件不存在"
            ;;
        3)
            echo "Nginx访问日志:"
            tail -f /var/log/nginx/umeikouagent_access.log 2>/dev/null || echo "日志文件不存在"
            ;;
        4)
            echo "Nginx错误日志:"
            tail -f /var/log/nginx/umeikouagent_error.log 2>/dev/null || echo "日志文件不存在"
            ;;
        5)
            echo "系统服务日志:"
            journalctl -u umeikouagent.service -f
            ;;
        *)
            echo "无效选择"
            ;;
    esac
}

stop_services() {
    echo "🛑 停止服务"
    echo "==========="
    
    # 停止开发环境
    pkill -f "manage.py runserver" 2>/dev/null && echo "✅ 开发服务器已停止"
    
    # 停止生产环境
    if [ "$EUID" -eq 0 ]; then
        systemctl stop umeikouagent.service 2>/dev/null && echo "✅ 生产应用已停止"
    else
        echo "⚠️  需要root权限停止生产环境服务"
    fi
}

restart_services() {
    echo "🔄 重启服务"
    echo "==========="
    
    if [ "$EUID" -eq 0 ]; then
        systemctl restart umeikouagent.service
        systemctl restart nginx
        echo "✅ 生产环境服务已重启"
    else
        echo "❌ 需要root权限重启生产环境服务"
        echo "请使用: sudo $0 restart"
    fi
}

backup_data() {
    echo "💾 备份数据"
    echo "==========="
    
    BACKUP_DIR="backups"
    mkdir -p "$BACKUP_DIR"
    
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    
    # 备份开发数据库
    if [ -f "db.sqlite3" ]; then
        cp db.sqlite3 "$BACKUP_DIR/dev_db_$TIMESTAMP.sqlite3"
        echo "✅ 开发数据库已备份: $BACKUP_DIR/dev_db_$TIMESTAMP.sqlite3"
    fi
    
    # 备份生产数据库
    if [ -f "production.db" ]; then
        cp production.db "$BACKUP_DIR/prod_db_$TIMESTAMP.sqlite3"
        echo "✅ 生产数据库已备份: $BACKUP_DIR/prod_db_$TIMESTAMP.sqlite3"
    fi
    
    # 备份静态文件
    if [ -d "staticfiles" ]; then
        tar -czf "$BACKUP_DIR/staticfiles_$TIMESTAMP.tar.gz" staticfiles/
        echo "✅ 静态文件已备份: $BACKUP_DIR/staticfiles_$TIMESTAMP.tar.gz"
    fi
    
    echo "📁 备份目录: $BACKUP_DIR"
}

# 主逻辑
case "$1" in
    dev)
        start_dev
        ;;
    prod)
        start_prod
        ;;
    deploy)
        deploy_prod
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    backup)
        backup_data
        ;;
    help|--help|-h)
        show_help
        ;;
    "")
        show_help
        ;;
    *)
        echo "❌ 未知命令: $1"
        echo ""
        show_help
        exit 1
        ;;
esac