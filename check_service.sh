#!/bin/bash

# 服务健康检查脚本

echo "=========================================="
echo "Umeikou 阅读分享 - 服务状态检查"
echo "检查时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""

# 检查 Django 应用服务
echo "📱 Django 应用服务状态:"
systemctl is-active umeikouagent.service > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ umeikouagent.service 运行中"
    echo "   进程数: $(systemctl show umeikouagent.service -p MainPID --value | xargs ps --no-headers -o pid,cmd -p 2>/dev/null | wc -l)"
else
    echo "❌ umeikouagent.service 未运行"
fi
echo ""

# 检查 Nginx 服务
echo "🌐 Nginx 服务状态:"
systemctl is-active nginx.service > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ nginx.service 运行中"
else
    echo "❌ nginx.service 未运行"
fi
echo ""

# 检查定时任务
echo "⏰ 定时任务状态:"
systemctl is-active weekly-digest.timer > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ weekly-digest.timer 已启用"
    echo "   下次执行: $(systemctl list-timers weekly-digest.timer --no-pager | grep weekly-digest | awk '{print $1, $2, $3}')"
else
    echo "❌ weekly-digest.timer 未启用"
fi
echo ""

# 检查端口监听
echo "🔌 端口监听状态:"
netstat -tlnp 2>/dev/null | grep -E ':(8000|80) ' > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ 端口 8000 (Gunicorn): $(netstat -tlnp 2>/dev/null | grep ':8000 ' | awk '{print $7}')"
    echo "✅ 端口 80 (Nginx): $(netstat -tlnp 2>/dev/null | grep ':80 ' | awk '{print $7}')"
else
    echo "❌ 端口未正常监听"
fi
echo ""

# 检查应用响应
echo "🌍 应用响应测试:"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000 2>/dev/null)
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ 应用响应正常 (HTTP $HTTP_CODE)"
else
    echo "❌ 应用响应异常 (HTTP $HTTP_CODE)"
fi
echo ""

# 检查日志文件
echo "📋 最近日志 (最后5行):"
if [ -f "/usr/Project/article_collection_django/logs/error.log" ]; then
    echo "错误日志:"
    tail -n 5 /usr/Project/article_collection_django/logs/error.log
else
    echo "⚠️  日志文件不存在"
fi
echo ""

# 检查磁盘空间
echo "💾 磁盘使用情况:"
df -h /usr/Project/article_collection_django | tail -n 1
echo ""

echo "=========================================="
echo "检查完成"
echo "=========================================="
