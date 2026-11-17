#!/usr/bin/env python
"""
测试邮件订阅功能
"""

import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'article_collection_django.settings')
django.setup()

from articles.models import Subscriber, EmailSendConfig, EmailSendLog
from articles.subscription_service import SubscriptionService

def test_subscription_feature():
    """测试订阅功能"""
    
    print("🧪 测试邮件订阅功能")
    print("=" * 50)
    
    # 1. 测试邮箱验证
    print("\n📧 测试邮箱格式验证:")
    test_emails = [
        ("test@example.com", True),
        ("invalid-email", False),
        ("test@", False),
        ("@example.com", False),
        ("user.name+tag@domain.co.uk", True),
    ]
    
    for email, expected in test_emails:
        valid, msg = SubscriptionService.validate_email(email)
        status = "✓" if valid == expected else "✗"
        print(f"  {status} {email}: {msg}")
    
    # 2. 测试验证码生成
    print("\n🔢 测试验证码生成:")
    captcha_id, question = SubscriptionService.generate_captcha()
    print(f"  验证码ID: {captcha_id[:8]}...")
    print(f"  问题: {question}")
    
    # 3. 测试统计数据
    print("\n📊 测试统计数据:")
    stats = SubscriptionService.get_statistics()
    print(f"  当前订阅人数: {stats['total_active']}")
    print(f"  今日新增: {stats['today_new']}")
    print(f"  已退订: {stats['total_unsubscribed']}")
    print(f"  近7天数据: {stats['daily_data']}")
    
    # 4. 测试发送配置
    print("\n⚙️ 测试发送配置:")
    config = SubscriptionService.get_send_config()
    print(f"  发送时间: 每{config.get_send_weekday_display()} {config.send_hour:02d}:{config.send_minute:02d}")
    print(f"  启用状态: {'已启用' if config.is_enabled else '已禁用'}")
    
    # 5. 数据库模型检查
    print("\n🗄️ 数据库模型检查:")
    print(f"  Subscriber 表: {Subscriber.objects.count()} 条记录")
    print(f"  EmailSendConfig 表: {EmailSendConfig.objects.count()} 条记录")
    print(f"  EmailSendLog 表: {EmailSendLog.objects.count()} 条记录")
    
    # 6. URL测试提示
    print("\n🌐 网页访问测试:")
    print("  📍 首页（含订阅表单）: http://localhost:8000/articles/")
    print("  📍 订阅管理后台: http://localhost:8000/articles/admin/subscription/")
    print("  📍 订阅者列表: http://localhost:8000/articles/admin/subscription/list/")
    print("  📍 发送配置: http://localhost:8000/articles/admin/subscription/config/")
    
    print("\n✅ 订阅功能测试完成!")
    return True

if __name__ == '__main__':
    test_subscription_feature()
