#!/bin/bash

# 生产环境启动脚本

echo "🚀 启动 Umeikou 的阅读分享 - 生产环境"
echo "=================================="

# 设置环境变量
export DJANGO_SETTINGS_MODULE=article_collection_django.settings_production

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 创建必要的目录
mkdir -p logs
mkdir -p staticfiles
mkdir -p media

# 安装依赖
echo "📦 安装依赖包..."
pip3 install -r requirements.txt

# 数据库迁移
echo "🗄️  执行数据库迁移..."
python3 manage.py migrate --settings=article_collection_django.settings_production

# 收集静态文件
echo "📁 收集静态文件..."
python3 manage.py collectstatic --noinput --settings=article_collection_django.settings_production

# 创建超级用户 (如果不存在)
echo "👤 检查管理员用户..."
python3 manage.py shell --settings=article_collection_django.settings_production -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='umeikou').exists():
    User.objects.create_user('umeikou', password='Ccc123123')
    print('✅ 管理员用户已创建')
else:
    print('✅ 管理员用户已存在')
"

# 启动Gunicorn服务器
echo "🌐 启动Gunicorn服务器..."
gunicorn --bind 127.0.0.1:8000 \
         --workers 3 \
         --timeout 120 \
         --max-requests 1000 \
         --max-requests-jitter 100 \
         --preload \
         --access-logfile logs/access.log \
         --error-logfile logs/error.log \
         --log-level info \
         --env DJANGO_SETTINGS_MODULE=article_collection_django.settings_production \
         article_collection_django.wsgi:application