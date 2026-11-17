#!/bin/bash

# 设置周阅读合集自动生成定时任务

echo "🚀 设置周阅读合集自动生成定时任务..."

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo "❌ 请使用root权限运行此脚本"
    echo "使用方法: sudo bash setup_weekly_digest.sh"
    exit 1
fi

# 获取当前脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

echo "📁 项目目录: $PROJECT_DIR"

# 复制systemd服务文件
echo "📋 复制systemd服务文件..."
cp "$PROJECT_DIR/weekly-digest.service" /etc/systemd/system/
cp "$PROJECT_DIR/weekly-digest.timer" /etc/systemd/system/

# 更新服务文件中的工作目录
sed -i "s|WorkingDirectory=.*|WorkingDirectory=$PROJECT_DIR|g" /etc/systemd/system/weekly-digest.service

# 重新加载systemd配置
echo "🔄 重新加载systemd配置..."
systemctl daemon-reload

# 启用并启动定时器
echo "⏰ 启用周阅读合集定时器..."
systemctl enable weekly-digest.timer
systemctl start weekly-digest.timer

# 检查定时器状态
echo "📊 检查定时器状态..."
systemctl status weekly-digest.timer --no-pager

echo ""
echo "✅ 周阅读合集定时任务设置完成！"
echo ""
echo "📅 执行时间: 每周日晚上22:00"
echo "📝 日志查看: journalctl -u weekly-digest.service"
echo "⏰ 定时器状态: systemctl status weekly-digest.timer"
echo "🔧 手动执行: systemctl start weekly-digest.service"
echo ""
echo "🎯 下次执行时间:"
systemctl list-timers weekly-digest.timer --no-pager