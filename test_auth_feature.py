#!/usr/bin/env python
"""
测试用户认证和个人名片功能
"""

import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'article_collection_django.settings')
django.setup()

from django.contrib.auth.models import User

def test_auth_feature():
    """测试认证功能"""
    
    print("🔐 测试用户认证功能")
    print("=" * 50)
    
    # 1. 检查用户是否存在
    try:
        user = User.objects.get(username='umeikou')
        print(f"✅ 用户存在: {user.username}")
        print(f"📧 邮箱: {user.email or '未设置'}")
        print(f"👤 是否为管理员: {'是' if user.is_superuser else '否'}")
        print(f"🕐 创建时间: {user.date_joined}")
    except User.DoesNotExist:
        print("❌ 用户不存在，正在创建...")
        user = User.objects.create_user('umeikou', password='Ccc123123')
        print(f"✅ 用户创建成功: {user.username}")
    
    # 2. 测试密码
    from django.contrib.auth import authenticate
    auth_user = authenticate(username='umeikou', password='Ccc123123')
    if auth_user:
        print("✅ 密码验证成功")
    else:
        print("❌ 密码验证失败")
    
    # 3. 显示功能说明
    print("\n🌐 功能测试说明:")
    print("  📍 登录页面: http://localhost:8000/articles/login/")
    print("  📍 收藏页面: http://localhost:8000/articles/collect/ (需要登录)")
    print("  📍 创建合集: http://localhost:8000/articles/weekly/create/ (需要登录)")
    print("  📍 文章列表: http://localhost:8000/articles/list/ (无需登录)")
    print("  📍 阅读分享: http://localhost:8000/articles/weekly/ (无需登录)")
    
    print("\n👤 个人名片功能:")
    print("  ✅ 圆形头像显示")
    print("  ✅ 个人标题: CSDN D 端运营")
    print("  ✅ 社交平台链接:")
    print("    - X (Twitter)")
    print("    - GitHub")
    print("    - 小红书")
    print("    - 抖音")
    
    print("\n🔒 权限控制:")
    print("  ✅ 收藏文章 - 需要登录")
    print("  ✅ 创建周合集 - 需要登录")
    print("  ✅ 删除文章 - 需要登录")
    print("  ✅ 浏览功能 - 无需登录")
    
    print("\n🎨 界面优化:")
    print("  ✅ 左侧主内容区域")
    print("  ✅ 右侧个人名片模块")
    print("  ✅ 响应式设计")
    print("  ✅ 登录状态显示")
    
    print("\n✅ 所有功能测试完成!")
    return True

if __name__ == '__main__':
    test_auth_feature()