#!/usr/bin/env python
"""测试HTML格式邮件发送"""
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'article_collection_django.settings')
django.setup()

from articles.models import WeeklyDigest
from articles.email_sender import WeeklyDigestEmailSender

print('测试发送HTML格式周刊邮件')
print('=' * 50)

sender = WeeklyDigestEmailSender()
digest = WeeklyDigest.objects.first()

print(f'周刊: {digest.title}')
print('正在发送HTML格式邮件...')

result = sender.send_weekly_digest(digest)

print(f'\n发送结果: {result["message"]}')
print(f'  成功: {result["success_count"]}')
print(f'  失败: {result["failed_count"]}')

if result.get('errors'):
    print('\n错误详情:')
    for err in result['errors']:
        print(f'  - {err[:100]}')
