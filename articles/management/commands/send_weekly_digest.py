"""
发送周阅读合集邮件给所有活跃订阅者
"""

from django.core.management.base import BaseCommand
from articles.models import WeeklyDigest
from articles.email_sender import WeeklyDigestEmailSender


class Command(BaseCommand):
    help = '发送最新一期周阅读合集邮件给所有活跃订阅者'

    def add_arguments(self, parser):
        parser.add_argument(
            '--digest-id',
            type=int,
            help='指定要发送的周合集 ID，默认发送最新一期',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅打印将要发送的信息，不实际发送',
        )

    def handle(self, *args, **options):
        digest_id = options.get('digest_id')
        dry_run = options.get('dry_run')

        if digest_id:
            digest = WeeklyDigest.objects.filter(id=digest_id).first()
            if not digest:
                self.stdout.write(self.style.ERROR(f'未找到 ID={digest_id} 的周合集'))
                return
        else:
            digest = WeeklyDigest.objects.order_by('-week_start').first()
            if not digest:
                self.stdout.write(self.style.ERROR('数据库中没有任何周合集，请先运行 create_weekly_digest'))
                return

        self.stdout.write(f'目标周合集: {digest.title}')
        self.stdout.write(f'时间范围: {digest.week_start} - {digest.week_end}')
        self.stdout.write(f'包含文章: {digest.articles.count()} 篇')

        if dry_run:
            self.stdout.write(self.style.WARNING('--dry-run 模式，不实际发送'))
            return

        sender = WeeklyDigestEmailSender()
        if not sender.is_available():
            self.stdout.write(self.style.ERROR('邮件服务不可用，请检查邮件配置'))
            return

        result = sender.send_weekly_digest(digest)

        if result['success']:
            self.stdout.write(self.style.SUCCESS(
                f"发送完成: {result['success_count']}/{result['total']} 成功"
            ))
        else:
            self.stdout.write(self.style.ERROR(f"发送失败: {result['message']}"))

        if result.get('errors'):
            for err in result['errors']:
                self.stdout.write(self.style.ERROR(f'  - {err}'))
