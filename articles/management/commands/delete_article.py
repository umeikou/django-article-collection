"""
删除文章的管理命令
"""

from django.core.management.base import BaseCommand
from articles.models import Article


class Command(BaseCommand):
    help = '删除文章'

    def add_arguments(self, parser):
        parser.add_argument('--id', type=int, help='文章ID')
        parser.add_argument('--url', type=str, help='文章URL')
        parser.add_argument('--confirm', action='store_true', help='确认删除，跳过交互确认')

    def handle(self, *args, **options):
        article_id = options.get('id')
        article_url = options.get('url')
        confirm = options.get('confirm', False)
        
        if not article_id and not article_url:
            self.stdout.write(
                self.style.ERROR('请提供文章ID (--id) 或URL (--url)')
            )
            return
        
        try:
            if article_id:
                article = Article.objects.get(id=article_id)
            else:
                article = Article.objects.get(url=article_url)
            
            # 显示文章信息
            self.stdout.write(f'找到文章:')
            self.stdout.write(f'  ID: {article.id}')
            self.stdout.write(f'  标题: {article.title or "无标题"}')
            self.stdout.write(f'  URL: {article.url}')
            self.stdout.write(f'  平台: {article.get_platform_display()}')
            self.stdout.write(f'  收藏时间: {article.collected_at}')
            
            # 确认删除
            if not confirm:
                response = input('\n确定要删除这篇文章吗？(y/N): ')
                if response.lower() != 'y':
                    self.stdout.write('取消删除')
                    return
            
            # 删除文章
            article.delete()
            self.stdout.write(
                self.style.SUCCESS(f'✓ 文章已删除')
            )
            
        except Article.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('文章不存在')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'删除失败: {e}')
            )