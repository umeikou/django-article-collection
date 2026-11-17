#!/bin/bash

# 生产环境部署脚本

echo "🚀 部署 Umeikou 的阅读分享到生产环境"
echo "======================================="

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo "❌ 请使用root权限运行此脚本"
    echo "使用方法: sudo bash deploy_production.sh"
    exit 1
fi

# 项目目录
PROJECT_DIR="/usr/Project/article_collection_django"
NGINX_SITES="/etc/nginx/sites-available"
NGINX_ENABLED="/etc/nginx/sites-enabled"

echo "📁 项目目录: $PROJECT_DIR"

# 1. 安装必要的软件包
echo "📦 安装必要软件包..."
apt update
apt install -y nginx python3-pip python3-venv gunicorn

# 2. 安装Python依赖
echo "🐍 安装Python依赖..."
cd $PROJECT_DIR
pip3 install -r requirements.txt
pip3 install gunicorn

# 3. 创建必要目录
echo "📁 创建目录结构..."
mkdir -p logs
mkdir -p staticfiles
mkdir -p media
chown -R www-data:www-data logs staticfiles media

# 4. 数据库设置
echo "🗄️  设置生产数据库..."
export DJANGO_SETTINGS_MODULE=article_collection_django.settings_production
python3 manage.py migrate
python3 manage.py collectstatic --noinput

# 复制测试数据到生产环境 (可选)
if [ -f "db.sqlite3" ]; then
    echo "📋 复制测试数据到生产环境..."
    cp db.sqlite3 production.db
    chown www-data:www-data production.db
fi

# 5. 配置Nginx
echo "🌐 配置Nginx..."
cp nginx_config.conf $NGINX_SITES/umeikouagent.top

# 启用站点
if [ ! -L "$NGINX_ENABLED/umeikouagent.top" ]; then
    ln -s $NGINX_SITES/umeikouagent.top $NGINX_ENABLED/umeikouagent.top
fi

# 测试Nginx配置
nginx -t
if [ $? -eq 0 ]; then
    echo "✅ Nginx配置测试通过"
else
    echo "❌ Nginx配置测试失败"
    exit 1
fi

# 6. 配置systemd服务
echo "⚙️  配置systemd服务..."
cp umeikouagent.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable umeikouagent.service

# 7. 配置定时任务
echo "⏰ 配置定时任务..."
cp weekly-digest.service /etc/systemd/system/
cp weekly-digest.timer /etc/systemd/system/
systemctl enable weekly-digest.timer
systemctl start weekly-digest.timer

# 8. 启动服务
echo "🚀 启动服务..."
systemctl start umeikouagent.service
systemctl reload nginx

# 9. 检查服务状态
echo "📊 检查服务状态..."
echo "Django应用状态:"
systemctl status umeikouagent.service --no-pager -l

echo "Nginx状态:"
systemctl status nginx --no-pager -l

echo "定时任务状态:"
systemctl status weekly-digest.timer --no-pager -l

# 10. 显示访问信息
echo ""
echo "🎉 部署完成!"
echo "=================================="
echo "🌐 网站地址: http://umeikouagent.top"
echo "🔐 管理员: umeikou / Ccc123123"
echo "📁 项目目录: $PROJECT_DIR"
echo "📋 日志目录: $PROJECT_DIR/logs"
echo ""
echo "📝 管理命令:"
echo "  重启应用: sudo systemctl restart umeikouagent.service"
echo "  重启Nginx: sudo systemctl restart nginx"
echo "  查看日志: sudo journalctl -u umeikouagent.service -f"
echo "  查看访问日志: sudo tail -f $PROJECT_DIR/logs/access.log"
echo ""
echo "⚠️  注意事项:"
echo "  1. 确保域名 umeikouagent.top 已正确解析到此服务器"
echo "  2. 如需HTTPS，请配置SSL证书"
echo "  3. 定期备份数据库文件: $PROJECT_DIR/production.db"