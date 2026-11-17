#!/bin/bash

# Umeikou 阅读分享 - 服务管理脚本

PROJECT_DIR="/usr/Project/article_collection_django"
SERVICE_NAME="umeikouagent.service"
TIMER_NAME="weekly-digest.timer"

show_help() {
    echo "🔧 Umeikou 阅读分享 - 服务管理工具"
    echo "=================================="
    echo ""
    echo "用法: $0 [命令]"
    echo ""
    echo "服务管理命令:"
    echo "  install     安装并启动所有服务"
    echo "  start       启动服务"
    echo "  stop        停止服务"
    echo "  restart     重启服务"
    echo "  status      查看服务状态"
    echo "  logs        查看实时日志"
    echo "  enable      启用开机自启"
    echo "  disable     禁用开机自启"
    echo ""
    echo "维护命令:"
    echo "  health      健康检查"
    echo "  backup      备份数据"
    echo "  update      更新服务配置"
    echo "  clean       清理日志文件"
    echo ""
    echo "示例:"
    echo "  $0 install   # 安装并启动服务"
    echo "  $0 status    # 查看服务状态"
    echo "  $0 logs      # 查看实时日志"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo "❌ 此操作需要root权限"
        echo "请使用: sudo $0 $1"
        exit 1
    fi
}

install_service() {
    echo "🚀 安装 Umeikou 阅读分享服务"
    echo "============================="
    
    check_root "install"
    
    cd "$PROJECT_DIR" || exit 1
    
    # 1. 创建必要目录
    echo "📁 创建目录结构..."
    mkdir -p logs staticfiles media
    chown -R nginx:nginx logs staticfiles media
    
    # 2. 安装Python依赖
    echo "🐍 安装Python依赖..."
    python3 -m pip install -r requirements.txt
    
    # 3. 数据库迁移
    echo "🗄️  数据库迁移..."
    export DJANGO_SETTINGS_MODULE=article_collection_django.settings_production
    python3 manage.py migrate
    python3 manage.py collectstatic --noinput
    
    # 4. 复制服务文件
    echo "⚙️  安装systemd服务..."
    cp umeikouagent.service /etc/systemd/system/
    cp weekly-digest.service /etc/systemd/system/
    cp weekly-digest.timer /etc/systemd/system/
    
    # 5. 重新加载systemd
    systemctl daemon-reload
    
    # 6. 启用并启动服务
    systemctl enable $SERVICE_NAME
    systemctl enable $TIMER_NAME
    systemctl start $SERVICE_NAME
    systemctl start $TIMER_NAME
    
    echo "✅ 服务安装完成!"
    show_status
}

start_service() {
    echo "🚀 启动服务..."
    check_root "start"
    
    systemctl start $SERVICE_NAME
    systemctl start nginx
    systemctl start $TIMER_NAME
    
    echo "✅ 服务已启动"
    show_status
}

stop_service() {
    echo "🛑 停止服务..."
    check_root "stop"
    
    systemctl stop $SERVICE_NAME
    systemctl stop $TIMER_NAME
    
    echo "✅ 服务已停止"
}

restart_service() {
    echo "🔄 重启服务..."
    check_root "restart"
    
    systemctl restart $SERVICE_NAME
    systemctl restart nginx
    
    echo "✅ 服务已重启"
    show_status
}

show_status() {
    echo "📊 服务状态检查"
    echo "==============="
    
    echo "🌐 Django应用:"
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo "  ✅ 运行中"
        echo "  📍 PID: $(systemctl show $SERVICE_NAME --property=MainPID --value)"
        echo "  ⏰ 运行时间: $(systemctl show $SERVICE_NAME --property=ActiveEnterTimestamp --value)"
    else
        echo "  ❌ 未运行"
    fi
    
    echo ""
    echo "🌐 Nginx:"
    if systemctl is-active --quiet nginx; then
        echo "  ✅ 运行中"
    else
        echo "  ❌ 未运行"
    fi
    
    echo ""
    echo "⏰ 定时任务:"
    if systemctl is-active --quiet $TIMER_NAME; then
        echo "  ✅ 运行中"
        echo "  📅 下次执行: $(systemctl list-timers $TIMER_NAME --no-pager | grep $TIMER_NAME | awk '{print $1, $2}')"
    else
        echo "  ❌ 未运行"
    fi
    
    echo ""
    echo "🔗 网络检查:"
    if netstat -tlnp 2>/dev/null | grep -q ":8000"; then
        echo "  ✅ 端口8000已监听"
    else
        echo "  ❌ 端口8000未监听"
    fi
    
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ | grep -q "200"; then
        echo "  ✅ HTTP服务正常"
    else
        echo "  ⚠️  HTTP服务异常"
    fi
}

show_logs() {
    echo "📋 实时日志查看"
    echo "==============="
    echo "按 Ctrl+C 退出日志查看"
    echo ""
    
    # 同时显示systemd日志和应用日志
    journalctl -u $SERVICE_NAME -f --no-pager &
    JOURNAL_PID=$!
    
    if [ -f "$PROJECT_DIR/logs/error.log" ]; then
        tail -f "$PROJECT_DIR/logs/error.log" &
        TAIL_PID=$!
    fi
    
    # 等待用户中断
    trap "kill $JOURNAL_PID $TAIL_PID 2>/dev/null; exit 0" INT
    wait
}

enable_service() {
    echo "🔧 启用开机自启..."
    check_root "enable"
    
    systemctl enable $SERVICE_NAME
    systemctl enable nginx
    systemctl enable $TIMER_NAME
    
    echo "✅ 开机自启已启用"
}

disable_service() {
    echo "🔧 禁用开机自启..."
    check_root "disable"
    
    systemctl disable $SERVICE_NAME
    systemctl disable $TIMER_NAME
    
    echo "✅ 开机自启已禁用"
}

health_check() {
    echo "🏥 健康检查"
    echo "==========="
    
    # 检查服务状态
    if ! systemctl is-active --quiet $SERVICE_NAME; then
        echo "❌ Django应用未运行"
        return 1
    fi
    
    # 检查端口
    if ! netstat -tlnp 2>/dev/null | grep -q ":8000"; then
        echo "❌ 端口8000未监听"
        return 1
    fi
    
    # 检查HTTP响应
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ || echo "000")
    if [ "$HTTP_CODE" != "200" ]; then
        echo "❌ HTTP服务异常 (状态码: $HTTP_CODE)"
        return 1
    fi
    
    # 检查数据库
    cd "$PROJECT_DIR" || exit 1
    export DJANGO_SETTINGS_MODULE=article_collection_django.settings_production
    if ! python3 manage.py check --deploy > /dev/null 2>&1; then
        echo "❌ Django配置检查失败"
        return 1
    fi
    
    echo "✅ 所有检查通过，服务运行正常"
    return 0
}

backup_data() {
    echo "💾 数据备份"
    echo "==========="
    
    BACKUP_DIR="$PROJECT_DIR/backups"
    mkdir -p "$BACKUP_DIR"
    
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    
    # 备份数据库
    if [ -f "$PROJECT_DIR/production.db" ]; then
        cp "$PROJECT_DIR/production.db" "$BACKUP_DIR/production_db_$TIMESTAMP.sqlite3"
        echo "✅ 数据库已备份: production_db_$TIMESTAMP.sqlite3"
    fi
    
    # 备份静态文件
    if [ -d "$PROJECT_DIR/staticfiles" ]; then
        tar -czf "$BACKUP_DIR/staticfiles_$TIMESTAMP.tar.gz" -C "$PROJECT_DIR" staticfiles/
        echo "✅ 静态文件已备份: staticfiles_$TIMESTAMP.tar.gz"
    fi
    
    # 备份日志
    if [ -d "$PROJECT_DIR/logs" ]; then
        tar -czf "$BACKUP_DIR/logs_$TIMESTAMP.tar.gz" -C "$PROJECT_DIR" logs/
        echo "✅ 日志文件已备份: logs_$TIMESTAMP.tar.gz"
    fi
    
    echo "📁 备份目录: $BACKUP_DIR"
}

update_service() {
    echo "🔄 更新服务配置..."
    check_root "update"
    
    cd "$PROJECT_DIR" || exit 1
    
    # 复制最新的服务文件
    cp umeikouagent.service /etc/systemd/system/
    cp weekly-digest.service /etc/systemd/system/
    cp weekly-digest.timer /etc/systemd/system/
    
    # 重新加载配置
    systemctl daemon-reload
    
    # 重启服务
    systemctl restart $SERVICE_NAME
    
    echo "✅ 服务配置已更新"
}

clean_logs() {
    echo "🧹 清理日志文件..."
    
    LOG_DIR="$PROJECT_DIR/logs"
    
    if [ -d "$LOG_DIR" ]; then
        # 保留最近7天的日志
        find "$LOG_DIR" -name "*.log" -type f -mtime +7 -delete
        find "$LOG_DIR" -name "*.log.*" -type f -mtime +7 -delete
        
        # 清理空文件
        find "$LOG_DIR" -empty -type f -delete
        
        echo "✅ 日志清理完成"
        echo "📊 当前日志大小: $(du -sh $LOG_DIR 2>/dev/null | cut -f1)"
    else
        echo "⚠️  日志目录不存在"
    fi
}

# 主逻辑
case "$1" in
    install)
        install_service
        ;;
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    enable)
        enable_service
        ;;
    disable)
        disable_service
        ;;
    health)
        health_check
        ;;
    backup)
        backup_data
        ;;
    update)
        update_service
        ;;
    clean)
        clean_logs
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