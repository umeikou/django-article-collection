#!/usr/bin/env python
"""
测试周刊邮件发送功能
"""

import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'article_collection_django.settings')
django.setup()

from articles.models import Subscriber, WeeklyDigest
from articles.email_sender import WeeklyDigestEmailSender, send_test_email

def test_email_sending():
    """测试邮件发送"""
    
    print("🧪 测试周刊邮件发送功能")
    print("=" * 50)
    
    # 1. 检查邮件服务
    print("\n📧 检查邮件服务:")
    sender = WeeklyDigestEmailSender()
    if sender.is_available():
        print("  ✓ 阿里云邮件服务已连接")
    else:
        print("  ✗ 邮件服务不可用，请检查配置")
        return False
    
    # 2. 检查周刊数据
    print("\n📚 检查周刊数据:")
    digest = WeeklyDigest.objects.first()
    if digest:
        print(f"  ✓ 最新周刊: {digest.title}")
        print(f"    时间范围: {digest.week_start} - {digest.week_end}")
        print(f"    文章数量: {digest.articles.count()}")
    else:
        print("  ✗ 没有周刊数据")
        return False
    
    # 3. 检查订阅者
    print("\n👥 检查订阅者:")
    subscribers = Subscriber.objects.filter(status='active')
    print(f"  活跃订阅者: {subscribers.count()} 人")
    for sub in subscribers[:5]:
        print(f"    - {sub.email}")
    
    # 4. 发送测试邮件
    print("\n📤 发送测试邮件:")
    test_email = input("  请输入测试邮箱地址 (直接回车跳过): ").strip()
    
    if test_email:
        print(f"  正在发送到 {test_email}...")
        result = send_test_email(test_email)
        if result['success']:
            print(f"  ✓ 发送成功! 周刊: {result.get('digest_title', '')}")
        else:
            print(f"  ✗ 发送失败: {result['message']}")
    else:
        print("  跳过测试邮件发送")
    
    # 5. 发送给所有订阅者
    if subscribers.count() > 0:
        print("\n📬 发送给所有订阅者:")
        confirm = input(f"  确认发送给 {subscribers.count()} 位订阅者? (y/N): ").strip().lower()
        
        if confirm == 'y':
            print("  正在发送...")
            result = sender.send_weekly_digest(digest)
            print(f"  发送结果: {result['message']}")
            print(f"    成功: {result['success_count']}")
            print(f"    失败: {result['failed_count']}")
            if result.get('errors'):
                print("  错误详情:")
                for err in result['errors'][:5]:
                    print(f"    - {err}")
        else:
            print("  已取消发送")
    
    print("\n✅ 测试完成!")
    return True

if __name__ == '__main__':
    test_email_sending()
