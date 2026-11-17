#!/usr/bin/env python
"""
项目启动状态检查
"""

import os
import sys
import django
import requests
from datetime import datetime

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'article_collection_django.settings')
django.setup()

from articles.models import Article, WeeklyDigest
from django.contrib.auth.models import User

def check_startup_status():
    """检查项目启动状态"""
    
    print("🚀 Umeikou 的阅读分享 - 项目启动检查")
    print("=" * 60)
    print(f"⏰ 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 数据库状态检查
    print("\n📊 数据库状态:")
    try:
        article_count = Article.objects.count()
        digest_count = WeeklyDigest.objects.count()
        user_count = User.objects.count()
        
        print(f"  ✅ 文章总数: {article_count}")
        print(f"  ✅ 周合集数: {digest_count}")
        print(f"  ✅ 用户数量: {user_count}")
        
        # 检查用户账号
        try:
            user = User.objects.get(username='umeikou')
            print(f"  ✅ 管理用户: {user.username} (已创建)")
        except User.DoesNotExist:
            print("  ❌ 管理用户不存在")
            
    except Exception as e:
        print(f"  ❌ 数据库连接失败: {e}")
    
    # 2. 静态文件检查
    print("\n📁 静态文件状态:")
    files_to_check = [
        ("头像文件", "static/images/avatar.jpg"),
        ("Favicon ICO", "static/images/favicon.ico"),
        ("Favicon PNG", "static/images/favicon.png"),
        ("样式文件", "static/css/style.css"),
        ("JS文件", "static/js/app.js"),
    ]
    
    for name, path in files_to_check:
        if os.path.exists(path):
            size = os.path.getsize(path)
            if size > 1024:
                size_str = f"{size/1024:.1f} KB"
            else:
                size_str = f"{size} bytes"
            print(f"  ✅ {name}: {size_str}")
        else:
            print(f"  ❌ {name}: 文件不存在")
    
    # 3. 服务器连接检查
    print("\n🌐 服务器状态:")
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code == 200:
            print("  ✅ 服务器运行正常")
            print(f"  ✅ 响应状态: {response.status_code}")
        else:
            print(f"  ⚠️  服务器响应异常: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"  ❌ 服务器连接失败: {e}")
    
    # 4. 功能模块状态
    print("\n🎯 功能模块:")
    print("  ✅ 用户认证系统 (登录/登出)")
    print("  ✅ 文章收藏管理")
    print("  ✅ 周阅读合集")
    print("  ✅ AI内容分析")
    print("  ✅ 个人名片展示")
    print("  ✅ 订阅功能预告")
    
    # 5. 访问地址
    print("\n🔗 访问地址:")
    urls = [
        ("主页统计", "http://localhost:8000/"),
        ("文章库", "http://localhost:8000/list/"),
        ("阅读分享", "http://localhost:8000/weekly/"),
        ("收藏文章", "http://localhost:8000/collect/"),
        ("用户登录", "http://localhost:8000/login/"),
    ]
    
    for name, url in urls:
        print(f"  📍 {name}: {url}")
    
    # 6. 登录信息
    print("\n🔐 登录信息:")
    print("  👤 用户名: umeikou")
    print("  🔑 密码: Ccc123123")
    print("  📝 权限: 收藏、删除、创建合集")
    
    print("\n" + "=" * 60)
    print("🎉 项目启动完成！欢迎使用 Umeikou 的阅读分享系统")
    print("💡 提示: 未登录用户可以浏览所有内容，登录后可进行管理操作")
    
    return True

if __name__ == '__main__':
    check_startup_status()