"""
创建周阅读合集的管理命令
用于定时任务自动生成周合集
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from articles.weekly_service import WeeklyDigestService


class Command(BaseCommand):
    help = '创建周阅读合集'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--week-offset',
            type=int,
            default=0,
            help='周偏移量，0表示本周，-1表示上周，1表示下周'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制重新创建，即使已存在'
        )
    
    def handle(self, *args, **options):
        week_offset = options['week_offset']
        force = options['force']
        
        service = WeeklyDigestService()
        
        # 计算目标周的日期
        today = timezone.now().date()
        target_date = today + timedelta(weeks=week_offset)
        week_start, week_end = service.get_week_range(target_date)
        
        self.stdout.write(f"正在处理 {week_start} 至 {week_end} 的周阅读合集...")
        
        # 检查是否已存在
        if not force:
            existing_digest = service.get_all_digests().filter(
                week_start=week_start,
                week_end=week_end
            ).first()
            
            if existing_digest:
                self.stdout.write(
                    self.style.WARNING(
                        f'该周合集已存在: {existing_digest.title}'
                    )
                )
                return
        
        # 获取该周的文章
        articles = service.get_articles_for_week(week_start, week_end)
        
        if not articles:
            self.stdout.write(
                self.style.WARNING(
                    f'该周 ({week_start} - {week_end}) 没有收藏任何文章，跳过创建合集'
                )
            )
            return
        
        self.stdout.write(f"找到 {articles.count()} 篇文章")
        
        try:
            # 创建合集
            digest, created = service.create_weekly_digest(week_start, week_end)
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ 成功创建周阅读合集: {digest.title}'
                    )
                )
                self.stdout.write(f'  - 包含文章: {digest.articles.count()} 篇')
                self.stdout.write(f'  - AI总结: {len(digest.summary)} 字')
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'该周合集已存在: {digest.title}'
                    )
                )
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'✗ 创建周阅读合集失败: {str(e)}'
                )
            )
            raise e
        
        # 显示合集信息
        if digest:
            self.stdout.write("\n" + "="*50)
            self.stdout.write(f"合集标题: {digest.title}")
            self.stdout.write(f"时间范围: {digest.week_start} - {digest.week_end}")
            self.stdout.write(f"文章数量: {digest.articles.count()}")
            self.stdout.write(f"AI总结预览: {digest.summary[:100]}...")
            self.stdout.write("="*50)