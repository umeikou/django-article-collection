#!/bin/bash

# 服务监控和自动恢复脚本

PROJECT_DIR="/usr/Project/article_collection_django"
SERVICE_NAME="umeikouagent.service"
LOG_FILE="$PROJECT_DIR/logs/monitor.log"

# 创建日志目录
mkdir -p "$PROJECT_DIR/logs"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_service() {
    if systemctl is-active --quiet $SERVICE_NAME; then
        return 0
    else
        return 1
    fi
}

check_port() {
    if netstat -tlnp 2>/dev/null | grep -q ":8000"; then
        return 0
    else
        return 1
    fi
}

check_http() {
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 http://localhost:8000/ 2>/dev/null || echo "000")
    
    if [ "$http_code" = "200" ]; then
        return 0
    else
        log_message "HTTP检查失败，状态码: $http_code"
        return 1
    fi
}

restart_service() {
    log_message "⚠️  检测到服务异常，正在重启..."
    
    systemctl restart $SERVICE_NAME
    sleep 10
    
    if check_service && check_port; then
        log_message "✅ 服务重启成功"
        return 0
    else
        log_message "❌ 服务重启失败"
        return 1
    fi
}

send_alert() {
    local message="$1"
    log_message "🚨 告警: $message"
    
    # 这里可以添加邮件或其他通知方式
    # echo "$message" | mail -s "Umeikou服务告警" admin@example.com
}

main_monitor() {
    log_message "🔍 开始服务监控检查"
    
    # 检查systemd服务状态
    if ! check_service; then
        log_message "❌ systemd服务未运行"
        restart_service
        if ! check_service; then
            send_alert "systemd服务重启失败"
            exit 1
        fi
    fi
    
    # 检查端口监听
    if ! check_port; then
        log_message "❌ 端口8000未监听"
        restart_service
        if ! check_port; then
            send_alert "端口监听恢复失败"
            exit 1
        fi
    fi
    
    # 检查HTTP响应
    if ! check_http; then
        log_message "❌ HTTP服务异常"
        restart_service
        if ! check_http; then
            send_alert "HTTP服务恢复失败"
            exit 1
        fi
    fi
    
    log_message "✅ 所有检查通过，服务运行正常"
}

# 清理旧日志（保留最近30天）
cleanup_logs() {
    if [ -f "$LOG_FILE" ]; then
        # 如果日志文件大于10MB，则轮转
        if [ $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null || echo 0) -gt 10485760 ]; then
            mv "$LOG_FILE" "${LOG_FILE}.old"
            log_message "📋 日志文件已轮转"
        fi
    fi
}

# 主执行逻辑
case "${1:-monitor}" in
    monitor)
        cleanup_logs
        main_monitor
        ;;
    test)
        echo "🧪 测试模式"
        main_monitor
        ;;
    *)
        echo "用法: $0 [monitor|test]"
        exit 1
        ;;
esac