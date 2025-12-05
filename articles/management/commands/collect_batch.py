"""
批量收藏文章的管理命令
"""

from django.core.management.base import BaseCommand
from articles.services import ArticleCollectionService


class Command(BaseCommand):
    help = '批量收藏文章'

    def add_arguments(self, parser):
        parser.add_argument('file', type=str, help='包含URL列表的文件路径')

    def handle(self, *args, **options):
        file_path = options['file']
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            self.stdout.write(f'开始批量收藏 {len(urls)} 篇文章...')
            
            service = ArticleCollectionService()
            result = service.collect_batch_articles(urls)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ 完成! 成功 {result["success"]}/{result["total"]} 篇文章'
                )
            )
            
            # 显示详细结果
            for item in result['results']:
                if item['success']:
                    self.stdout.write(f'  ✓ {item["url"]}')
                else:
                    self.stdout.write(f'  ✗ {item["url"]} - {item["message"]}')
                    
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(f'文件不存在: {file_path}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'错误: {e}')
            )