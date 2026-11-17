#!/usr/bin/env python
"""
测试周阅读分享功能
"""

import os
import sys
import django
from datetime import datetime

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'article_collection_django.settings')
django.setup()

from articles.models import Article, WeeklyDigest
from articles.weekly_service import WeeklyDigestService

def test_weekly_digest_feature():
    """测试周阅读合集功能"""
    
    print("🧪 测试周阅读分享功能")
    print("=" * 50)
    
    # 1. 检查文章数据
    total_articles = Article.objects.count()
    print(f"📚 总文章数: {total_articles}")
    
    # 2. 检查周合集
    total_digests = WeeklyDigest.objects.count()
    print(f"📖 总合集数: {total_digests}")
    
    if total_digests > 0:
        latest_digest = WeeklyDigest.objects.first()
        print(f"📅 最新合集: {latest_digest.title}")
        print(f"🗓️  时间范围: {latest_digest.week_start} - {latest_digest.week_end}")
        print(f"📄 包含文章: {latest_digest.articles.count()} 篇")
        print(f"🤖 AI总结长度: {len(latest_digest.summary)} 字")
        print(f"💡 总结预览: {latest_digest.summary[:100]}...")
    
    # 3. 测试服务功能
    print("\n🔧 测试服务功能:")
    service = WeeklyDigestService()
    
    # 获取本周日期范围
    week_start, week_end = service.get_week_range()
    print(f"📅 本周范围: {week_start} - {week_end}")
    
    # 获取本周文章
    week_articles = service.get_articles_for_week(week_start, week_end)
    print(f"📚 本周文章: {week_articles.count()} 篇")
    
    # 4. 显示文章详情
    if week_articles.exists():
        print("\n📋 本周文章列表:")
        for i, article in enumerate(week_articles[:5], 1):
            print(f"  {i}. {article.title or '无标题'} ({article.platform})")
            if article.ai_key_point:
                print(f"     💡 核心观点: {article.ai_key_point[:50]}...")
        
        if week_articles.count() > 5:
            print(f"     ... 还有 {week_articles.count() - 5} 篇文章")
    
    # 5. URL测试提示
    print("\n🌐 网页访问测试:")
    print("  📍 阅读分享列表: http://localhost:8000/articles/weekly/")
    if total_digests > 0:
        print(f"  📍 最新合集详情: http://localhost:8000/articles/weekly/{latest_digest.id}/")
    print("  📍 创建新合集: http://localhost:8000/articles/weekly/create/")
    
    print("\n✅ 功能测试完成!")
    return True

if __name__ == '__main__':
    test_weekly_digest_feature()