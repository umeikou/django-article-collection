"""
重新分析文章的管理命令
"""

from django.core.management.base import BaseCommand
from articles.models import Article
from articles.ai_service import get_ai_service


class Command(BaseCommand):
    help = '使用AI重新分析已收藏的文章'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='分析所有文章（包括已分析过的）'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='限制分析数量（默认10篇）'
        )
        parser.add_argument(
            '--id',
            type=int,
            help='分析指定ID的文章'
        )

    def handle(self, *args, **options):
        ai_service = get_ai_service()
        
        if not ai_service.is_available():
            self.stdout.write(
                self.style.ERROR('❌ AI服务不可用，请设置 DEEPSEEK_API_KEY 环境变量')
            )
            return
        
        # 获取要分析的文章
        if options['id']:
            # 分析指定文章
            try:
                articles = [Article.objects.get(id=options['id'])]
            except Article.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'文章ID {options["id"]} 不存在')
                )
                return
        elif options['all']:
            # 分析所有有内容的文章
            articles = Article.objects.filter(
                content__isnull=False
            ).exclude(content='')[:options['limit']]
        else:
            # 只分析未分析过的文章
            articles = Article.objects.filter(
                content__isnull=False,
                ai_summary__isnull=True
            ).exclude(content='')[:options['limit']]
        
        total = len(articles)
        
        if total == 0:
            self.stdout.write('没有需要分析的文章')
            return
        
        self.stdout.write(f'开始分析 {total} 篇文章...\n')
        
        success_count = 0
        
        for index, article in enumerate(articles, 1):
            self.stdout.write(f'[{index}/{total}] 分析: {article.title or article.url}')
            
            try:
                # 调用AI分析
                result = ai_service.analyze_article(
                    content=article.content,
                    title=article.title or ''
                )
                
                # 更新文章
                article.ai_key_point = result.get('key_point', '')
                article.ai_summary = result.get('summary', '')
                article.save()
                
                success_count += 1
                
                # 显示结果
                if result.get('key_point'):
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ 核心观点: {result["key_point"][:60]}...')
                    )
                if result.get('summary'):
                    self.stdout.write(
                        f'  ✓ 摘要: {result["summary"][:80]}...'
                    )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ 分析失败: {str(e)}')
                )
            
            self.stdout.write('')  # 空行
        
        # 总结
        self.stdout.write(
            self.style.SUCCESS(f'\n✓ 完成! 成功分析 {success_count}/{total} 篇文章')
        )