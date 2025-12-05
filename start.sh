#!/bin/bash

echo "🚀 启动文章收藏系统 Django 版本..."

# 检查依赖
echo "📦 检查依赖..."
pip3 install -r requirements.txt

# 运行迁移
echo "🗄️ 运行数据库迁移..."
python3 manage.py migrate

# 收集静态文件
echo "📁 收集静态文件..."
python3 manage.py collectstatic --noinput

# 启动服务器
echo "🌐 启动开发服务器..."
echo "📝 Web界面: http://localhost:8000"
echo "🔧 管理后台: http://localhost:8000/admin (用户名: admin, 密码: admin123)"
echo "📡 API接口: http://localhost:8000/api/articles/"

python3 manage.py runserver 0.0.0.0:8000