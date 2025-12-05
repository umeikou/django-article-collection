"""
显示统计信息的管理命令
"""

from django.core.management.base import BaseCommand
from django.db.models import Count
from articles.models import Article


class Command(BaseCommand):
    help = '显示收藏统计信息'

    def handle(self, *args, **options):
        total = Article.objects.count()
        
        self.stdout.write('📊 收藏统计:')
        self.stdout.write(f'  总文章数: {total}')
        
        if total > 0:
            # 按平台统计
            platform_stats = Article.objects.values('platform').annotate(
                count=Count('id')
            ).order_by('-count')
            
            self.stdout.write('\n按平台分布:')
            for stat in platform_stats:
                platform_name = dict(Article.PLATFORM_CHOICES).get(
                    stat['platform'], stat['platform']
                )
                self.stdout.write(f'  {platform_name}: {stat["count"]}')
            
            # 最新收藏
            recent = Article.objects.order_by('-collected_at')[:5]
            self.stdout.write('\n最新收藏:')
            for article in recent:
                self.stdout.write(
                    f'  [{article.get_platform_display()}] {article.title or "无标题"}'
                )
        else:
            self.stdout.write('  暂无收藏的文章')