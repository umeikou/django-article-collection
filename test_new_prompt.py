#!/usr/bin/env python
"""
测试新的周阅读总结 prompt 格式
"""

import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'article_collection_django.settings')
django.setup()

from articles.models import Article
from articles.weekly_service import WeeklyDigestService

def test_new_prompt_format():
    """测试新的prompt格式"""
    
    print("🧪 测试新的周阅读总结 prompt 格式")
    print("=" * 50)
    
    service = WeeklyDigestService()
    
    # 获取一些示例文章
    articles = Article.objects.all()[:3]
    
    if not articles:
        print("❌ 没有找到文章数据，请先收藏一些文章")
        return False
    
    print(f"📚 使用 {len(articles)} 篇文章进行测试:")
    for i, article in enumerate(articles, 1):
        print(f"  {i}. {article.title or '无标题'}")
        if article.ai_key_point:
            print(f"     💡 {article.ai_key_point[:50]}...")
    
    print("\n🤖 生成新格式总结...")
    
    try:
        summary = service.generate_weekly_summary(articles)
        print("\n📝 生成的总结:")
        print("-" * 30)
        print(summary)
        print("-" * 30)
        
        # 检查格式要求
        print("\n✅ 格式检查:")
        has_insight = "💡 核心洞察" in summary
        has_overview = "📍 重点速览" in summary  
        has_comment = "💬 一句点评" in summary
        
        print(f"  💡 包含核心洞察: {'✓' if has_insight else '✗'}")
        print(f"  📍 包含重点速览: {'✓' if has_overview else '✗'}")
        print(f"  💬 包含一句点评: {'✓' if has_comment else '✗'}")
        
        # 检查是否避免了空洞词汇
        bad_words = ['底层逻辑', '赋能', '抓手', '闭环', '降本增效', '生态']
        has_bad_words = any(word in summary for word in bad_words)
        print(f"  🚫 避免空洞词汇: {'✓' if not has_bad_words else '✗'}")
        
        if has_bad_words:
            found_words = [word for word in bad_words if word in summary]
            print(f"     发现的空洞词汇: {', '.join(found_words)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 生成总结失败: {e}")
        return False

if __name__ == '__main__':
    test_new_prompt_format()