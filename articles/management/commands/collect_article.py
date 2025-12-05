"""
收藏文章的管理命令
"""

from django.core.management.base import BaseCommand
from articles.services import ArticleCollectionService


class Command(BaseCommand):
    help = '收藏文章'

    def add_arguments(self, parser):
        parser.add_argument('url', type=str, help='文章URL')

    def handle(self, *args, **options):
        url = options['url']
        
        self.stdout.write(f'正在收藏: {url}')
        
        service = ArticleCollectionService()
        success, message, article = service.collect_article(url)
        
        if success:
            self.stdout.write(
                self.style.SUCCESS(f'✓ {message}')
            )
            if article:
                self.stdout.write(f'标题: {article.title}')
                self.stdout.write(f'平台: {article.get_platform_display()}')
        else:
            self.stdout.write(
                self.style.ERROR(f'✗ {message}')
            )