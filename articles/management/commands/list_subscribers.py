"""
列出邮件订阅者
用法:
  python manage.py list_subscribers                # 全部
  python manage.py list_subscribers --status active
  python manage.py list_subscribers --status unsubscribed
  python manage.py list_subscribers --csv          # 导出 CSV 到 stdout
  python manage.py list_subscribers --csv > subs.csv
"""

import csv
import sys
from django.core.management.base import BaseCommand
from django.utils import timezone
from articles.models import Subscriber


class Command(BaseCommand):
    help = "列出所有邮件订阅者，可按状态过滤或导出 CSV"

    def add_arguments(self, parser):
        parser.add_argument(
            "--status",
            choices=["active", "unsubscribed", "all"],
            default="all",
            help="按状态过滤,默认全部",
        )
        parser.add_argument(
            "--csv",
            action="store_true",
            help="以 CSV 格式输出(可重定向到文件)",
        )

    def handle(self, *args, **opts):
        qs = Subscriber.objects.all().order_by("-subscribed_at")
        if opts["status"] != "all":
            qs = qs.filter(status=opts["status"])

        if opts["csv"]:
            self._write_csv(qs)
            return

        self._write_table(qs, opts["status"])

    def _write_csv(self, qs):
        writer = csv.writer(sys.stdout)
        writer.writerow(["email", "status", "subscribed_at", "unsubscribed_at", "ip_address"])
        for s in qs:
            writer.writerow([
                s.email,
                s.status,
                s.subscribed_at.isoformat() if s.subscribed_at else "",
                s.unsubscribed_at.isoformat() if s.unsubscribed_at else "",
                s.ip_address or "",
            ])

    def _write_table(self, qs, status_filter):
        total_all = Subscriber.objects.count()
        active = Subscriber.objects.filter(status="active").count()
        unsub = Subscriber.objects.filter(status="unsubscribed").count()

        header = f"订阅者总览: {total_all} 人 (活跃 {active} / 已退订 {unsub})"
        if status_filter != "all":
            header += f"  · 当前过滤: status={status_filter} ({qs.count()})"
        self.stdout.write(header)
        self.stdout.write("=" * 96)

        if not qs.exists():
            self.stdout.write("(无匹配的订阅者)")
            return

        col = "{email:<32} {status:<14} {subscribed:<22} {unsubscribed:<22} {ip:<16}"
        self.stdout.write(col.format(
            email="邮箱", status="状态",
            subscribed="订阅时间(本地)", unsubscribed="退订时间(本地)", ip="IP",
        ))
        self.stdout.write("-" * 96)

        tz = timezone.get_current_timezone()
        for s in qs:
            sub_at = s.subscribed_at.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S") if s.subscribed_at else "-"
            unsub_at = s.unsubscribed_at.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S") if s.unsubscribed_at else "-"
            self.stdout.write(col.format(
                email=s.email,
                status=s.status,
                subscribed=sub_at,
                unsubscribed=unsub_at,
                ip=s.ip_address or "-",
            ))
