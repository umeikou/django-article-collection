#!/usr/bin/env python3
"""
文章收藏系统功能演示脚本
"""

import os
import sys
import django
import requests
import time

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'article_collection_django.settings')
django.setup()

from articles.models import Article
from articles.services import ArticleCollectionService

def demo_title_parsing():
    """演示标题解析功能"""
    print("🔍 演示标题解析功能")
    print("=" * 50)
    
    test_urls = [
        "https://www.python.org/",
        "https://github.com/django/django",
        "https://docs.djangoproject.com/",
        "https://stackoverflow.com/questions/tagged/python",
    ]
    
    service = ArticleCollectionService()
    
    for url in test_urls:
        print(f"\n正在解析: {url}")
        success, message, article = service.collect_article(url)
        
        if success and article:
            print(f"✓ 标题: {article.title}")
            print(f"  平台: {article.get_platform_display()}")
            if article.author:
                print(f"  作者: {article.author}")
            if article.content:
                print(f"  内容: {article.content[:100]}...")
        else:
            print(f"✗ 失败: {message}")
        
        time.sleep(1)  # 避免请求过快

def demo_api_operations():
    """演示API操作"""
    print("\n\n📡 演示API操作")
    print("=" * 50)
    
    base_url = "http://localhost:8000/api"
    
    # 1. 获取统计信息
    print("\n1. 获取统计信息:")
    response = requests.get(f"{base_url}/articles/statistics/")
    if response.status_code == 200:
        stats = response.json()
        print(f"   总文章数: {stats['total']}")
        print(f"   平台分布: {stats['by_platform']}")
    
    # 2. 收藏文章
    print("\n2. 通过API收藏文章:")
    test_url = "https://www.djangoproject.com/"
    response = requests.post(
        f"{base_url}/articles/collect/",
        json={"url": test_url},
        headers={"Content-Type": "application/json"}
    )
    if response.status_code == 201:
        result = response.json()
        print(f"   ✓ {result['message']}")
        if result.get('article'):
            print(f"   标题: {result['article']['title']}")
    
    # 3. 获取文章列表
    print("\n3. 获取文章列表:")
    response = requests.get(f"{base_url}/articles/?page_size=5")
    if response.status_code == 200:
        data = response.json()
        print(f"   共 {data['count']} 篇文章")
        for article in data['results'][:3]:
            print(f"   - {article['title'][:50]}...")

def demo_management_commands():
    """演示管理命令"""
    print("\n\n⚡ 演示管理命令")
    print("=" * 50)
    
    print("\n可用的管理命令:")
    print("1. python manage.py collect_article <url>     # 收藏单篇文章")
    print("2. python manage.py collect_batch <file>      # 批量收藏")
    print("3. python manage.py show_stats                # 显示统计")
    print("4. python manage.py delete_article --id <id>  # 删除文章")
    
    print("\n当前统计:")
    total = Article.objects.count()
    print(f"   总文章数: {total}")
    
    if total > 0:
        recent = Article.objects.order_by('-collected_at')[:3]
        print("   最新收藏:")
        for article in recent:
            print(f"   - [{article.get_platform_display()}] {article.title or '无标题'}")

def main():
    """主函数"""
    print("🚀 文章收藏系统功能演示")
    print("=" * 60)
    
    try:
        # 检查服务器是否运行
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code != 200:
            print("❌ 服务器未运行，请先启动: ./start.sh")
            return
    except requests.exceptions.RequestException:
        print("❌ 无法连接到服务器，请先启动: ./start.sh")
        return
    
    print("✓ 服务器运行正常")
    
    # 演示各项功能
    demo_title_parsing()
    demo_api_operations()
    demo_management_commands()
    
    print("\n\n🎉 演示完成！")
    print("\n访问地址:")
    print("- Web界面: http://localhost:8000")
    print("- 管理后台: http://localhost:8000/admin")
    print("- API文档: http://localhost:8000/api/articles/")

if __name__ == "__main__":
    main()