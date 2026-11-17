#!/usr/bin/env python
"""
演示数据脚本 - 为文章库添加示例数据
"""

import os
import sys
import django
from datetime import datetime, timedelta

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'article_collection_django.settings')
django.setup()

from articles.models import Article

def create_demo_articles():
    """创建演示文章数据"""
    
    demo_articles = [
        {
            'url': 'https://mp.weixin.qq.com/s/demo1',
            'title': 'AI大模型的未来发展趋势与挑战',
            'content': '随着人工智能技术的快速发展，大模型已经成为AI领域的重要突破。本文深入分析了当前大模型的技术现状、应用场景以及未来可能面临的挑战和机遇。从GPT到Claude，从文本生成到多模态理解，AI大模型正在重塑我们对人工智能的认知。',
            'author': '张三',
            'platform': 'weixin',
            'ai_key_point': 'AI大模型正在从单一文本处理向多模态理解转变，未来将在教育、医疗、创意等领域产生深远影响',
            'ai_summary': '文章详细分析了AI大模型的技术演进路径，指出当前模型在推理能力、知识更新、计算成本等方面仍存在挑战。作者认为，未来的发展方向将是更高效的模型架构、更好的人机协作模式，以及更广泛的行业应用。',
        },
        {
            'url': 'https://www.zhihu.com/question/demo2',
            'title': '如何在工作中有效运用时间管理技巧',
            'content': '时间管理是现代职场人士必备的核心技能。本文分享了多种实用的时间管理方法，包括番茄工作法、GTD系统、时间块规划等，帮助读者提高工作效率，实现工作与生活的平衡。',
            'author': '效率专家李四',
            'platform': 'zhihu',
            'ai_key_point': '有效的时间管理不是做更多事情，而是专注于最重要的事情，通过系统化方法提升执行力',
            'ai_summary': '作者从心理学和行为学角度解析了时间管理的本质，提出了"重要性矩阵"和"能量管理"的概念。文章强调，真正的时间管理是对注意力和精力的管理，而非简单的时间分配。',
        },
        {
            'url': 'https://www.xiaohongshu.com/explore/demo3',
            'title': '2024年最值得关注的设计趋势',
            'content': '设计行业每年都在快速演变，2024年也不例外。从极简主义到新拟物化设计，从暗黑模式到可持续设计理念，本文盘点了今年最具影响力的设计趋势，为设计师提供创作灵感。',
            'author': '设计师王五',
            'platform': 'xiaohongshu',
            'ai_key_point': '2024年设计趋势强调情感连接和可持续性，设计师需要在美学与功能性之间找到新的平衡点',
            'ai_summary': '文章通过大量案例分析了当前设计趋势的形成原因，指出用户对个性化和环保意识的提升正在推动设计理念的转变。作者预测，未来设计将更加注重用户体验和社会责任。',
        },
        {
            'url': 'https://web.okjike.com/originalPost/demo4',
            'title': '远程工作三年后的思考与总结',
            'content': '疫情改变了很多人的工作方式，远程工作从临时措施变成了长期选择。作为一名远程工作三年的从业者，我想分享一些关于远程工作的真实体验、挑战和收获。',
            'author': '数字游民赵六',
            'platform': 'jike',
            'ai_key_point': '远程工作的成功关键在于自律、沟通和边界管理，它既是自由的象征也是责任的体现',
            'ai_summary': '作者从个人经历出发，客观分析了远程工作的利弊。文章提到，远程工作提高了工作灵活性和生活质量，但也带来了沟通成本增加、团队协作难度提升等挑战。',
        },
        {
            'url': 'https://juejin.cn/post/demo5',
            'title': 'Vue 3.4 新特性深度解析',
            'content': 'Vue 3.4 版本带来了许多令人兴奋的新特性和性能优化。本文将深入解析这些更新，包括新的响应式系统改进、组合式API增强、以及开发者体验的提升。',
            'author': '前端工程师钱七',
            'platform': 'juejin',
            'ai_key_point': 'Vue 3.4 通过编译时优化和运行时性能提升，为开发者提供了更好的开发体验和更高的应用性能',
            'ai_summary': '文章详细介绍了Vue 3.4的核心改进，包括更智能的响应式系统、更好的TypeScript支持、以及新的开发工具。作者通过代码示例展示了如何利用这些新特性优化现有项目。',
        },
        {
            'url': 'https://blog.csdn.net/demo6',
            'title': 'Docker容器化部署最佳实践指南',
            'content': 'Docker已经成为现代应用部署的标准工具。本文总结了Docker容器化部署的最佳实践，包括镜像优化、安全配置、监控策略等，帮助开发者构建更稳定、更安全的容器化应用。',
            'author': '运维工程师孙八',
            'platform': 'csdn',
            'ai_key_point': '成功的容器化部署需要在镜像大小、安全性、可维护性之间找到平衡，关键是建立标准化的流程',
            'ai_summary': '作者基于多年运维经验，提出了容器化部署的完整方法论。文章涵盖了从开发环境到生产环境的全流程最佳实践，特别强调了安全性和可观测性的重要性。',
        }
    ]
    
    created_count = 0
    updated_count = 0
    
    for article_data in demo_articles:
        # 检查文章是否已存在
        existing_article = Article.objects.filter(url=article_data['url']).first()
        
        if existing_article:
            # 更新现有文章的AI字段
            existing_article.ai_key_point = article_data['ai_key_point']
            existing_article.ai_summary = article_data['ai_summary']
            if not existing_article.title:
                existing_article.title = article_data['title']
            if not existing_article.content:
                existing_article.content = article_data['content']
            if not existing_article.author:
                existing_article.author = article_data['author']
            existing_article.save()
            updated_count += 1
            print(f"✓ 更新文章: {article_data['title']}")
        else:
            # 创建新文章
            Article.objects.create(**article_data)
            created_count += 1
            print(f"✓ 创建文章: {article_data['title']}")
    
    print(f"\n演示数据创建完成!")
    print(f"新创建: {created_count} 篇文章")
    print(f"更新: {updated_count} 篇文章")
    print(f"总计: {Article.objects.count()} 篇文章")

if __name__ == '__main__':
    create_demo_articles()