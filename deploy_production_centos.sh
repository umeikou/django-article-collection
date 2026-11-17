#!/bin/bash

# CentOS/RHEL/Alibaba Cloud Linux 生产环境部署脚本

echo "🚀 部署 Umeikou 的阅读分享到生产环境 (CentOS/RHEL)"
echo "=================================================="

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo "❌ 请使用root权限运行此脚本"
    echo "使用方法: sudo bash deploy_production_centos.sh"
    exit 1
fi

# 项目目录
PROJECT_DIR="/usr/Project/article_collection_django"
NGINX_CONF="/etc/nginx/conf.d"

echo "📁 项目目录: $PROJECT_DIR"

# 1. 安装必要的软件包
echo "📦 安装必要软件包..."
yum update -y
yum install -y nginx python3 python3-pip

# 启用EPEL仓库 (如果需要)
yum install -y epel-release

# 2. 安装Python依赖
echo "🐍 安装Python依赖..."
cd $PROJECT_DIR
pip3 install -r requirements.txt

# 3. 创建必要目录和用户
echo "📁 创建目录结构..."
mkdir -p logs
mkdir -p staticfiles
mkdir -p media

# 创建nginx用户 (如果不存在)
if ! id "nginx" &>/dev/null; then
    useradd -r -s /bin/false nginx
fi

# 设置目录权限
chown -R nginx:nginx logs staticfiles media
chmod 755 logs staticfiles media

# 4. 数据库设置
echo "🗄️  设置生产数据库..."
export DJANGO_SETTINGS_MODULE=article_collection_django.settings_production
python3 manage.py migrate
python3 manage.py collectstatic --noinput

# 复制测试数据到生产环境 (可选)
if [ -f "db.sqlite3" ]; then
    echo "📋 复制测试数据到生产环境..."
    cp db.sqlite3 production.db
    chown nginx:nginx production.db
fi

# 5. 配置Nginx
echo "🌐 配置Nginx..."
# 创建Nginx配置目录 (如果不存在)
mkdir -p $NGINX_CONF

# 复制配置文件
cat > $NGINX_CONF/umeikouagent.conf << 'EOF'
server {
    listen 80;
    server_name umeikouagent.top www.umeikouagent.top;
    
    # 项目根目录
    root /usr/Project/article_collection_django;
    
    # 日志文件
    access_log /var/log/nginx/umeikouagent_access.log;
    error_log /var/log/nginx/umeikouagent_error.log;
    
    # 静态文件处理
    location /static/ {
        alias /usr/Project/article_collection_django/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
        
        # 压缩静态文件
        gzip on;
        gzip_types text/css application/javascript image/svg+xml;
    }
    
    # 媒体文件处理
    location /media/ {
        alias /usr/Project/article_collection_django/media/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }
    
    # Favicon处理
    location /favicon.ico {
        alias /usr/Project/article_collection_django/staticfiles/images/favicon.ico;
        expires 30d;
    }
    
    # 主应用代理
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # 缓冲设置
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }
    
    # 安全头设置
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # 隐藏Nginx版本
    server_tokens off;
    
    # 限制请求大小
    client_max_body_size 10M;
}
EOF

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
cat > /etc/systemd/system/umeikouagent.service << 'EOF'
[Unit]
Description=Umeikou Reading Share - Django Application
After=network.target

[Service]
Type=exec
User=nginx
Group=nginx
WorkingDirectory=/usr/Project/article_collection_django
Environment=DJANGO_SETTINGS_MODULE=article_collection_django.settings_production
Environment=PYTHONPATH=/usr/Project/article_collection_django
ExecStart=/usr/local/bin/gunicorn --bind 127.0.0.1:8000 --workers 3 --timeout 120 --max-requests 1000 --max-requests-jitter 100 --preload --access-logfile /usr/Project/article_collection_django/logs/access.log --error-logfile /usr/Project/article_collection_django/logs/error.log --log-level info article_collection_django.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

# 安全设置
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/usr/Project/article_collection_django

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable umeikouagent.service

# 7. 配置定时任务
echo "⏰ 配置定时任务..."
cp weekly-digest.service /etc/systemd/system/
cp weekly-digest.timer /etc/systemd/system/
systemctl enable weekly-digest.timer
systemctl start weekly-digest.timer

# 8. 配置防火墙
echo "🔥 配置防火墙..."
if command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-service=http
    firewall-cmd --permanent --add-service=https
    firewall-cmd --reload
    echo "✅ 防火墙配置完成"
fi

# 9. 启动服务
echo "🚀 启动服务..."
systemctl enable nginx
systemctl start nginx
systemctl start umeikouagent.service

# 10. 检查服务状态
echo "📊 检查服务状态..."
echo "Django应用状态:"
systemctl status umeikouagent.service --no-pager -l

echo "Nginx状态:"
systemctl status nginx --no-pager -l

echo "定时任务状态:"
systemctl status weekly-digest.timer --no-pager -l

# 11. 显示访问信息
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
echo ""
echo "🔧 故障排除:"
echo "  检查端口: netstat -tlnp | grep :8000"
echo "  检查进程: ps aux | grep gunicorn"
echo "  测试配置: nginx -t"