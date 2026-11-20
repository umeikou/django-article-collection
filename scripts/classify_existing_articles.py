# -*- coding: utf-8 -*-
"""一次性脚本：为存量文章批量执行主题分类（v2.2.0）。

用法（服务器上，需加载 .env 与生产 settings）：
    cd /usr/Project/article_collection_django
    set -a && source .env && set +a
    DJANGO_SETTINGS_MODULE=article_collection_django.settings_production \
        python3 scripts/classify_existing_articles.py [--dry-run] [--only-misc]

规则：以标题 + AI 摘要（无摘要则正文前 800 字）调用 classify_category；
已有非 misc 分类的文章默认跳过（--force 可覆盖）。
"""
import os
import sys
import time

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'article_collection_django.settings_production')
django.setup()

from articles.models import Article  # noqa: E402
from articles.ai_service import DeepSeekAIService  # noqa: E402


def main():
    dry_run = '--dry-run' in sys.argv
    force = '--force' in sys.argv

    qs = Article.objects.all().order_by('-collected_at')
    if not force:
        qs = qs.filter(category='misc')

    service = DeepSeekAIService()
    if not service.is_available():
        print('DeepSeek 不可用（DEEPSEEK_API_KEY 未配置），退出。')
        sys.exit(1)

    total = qs.count()
    print(f'待分类文章：{total} 篇{"（dry-run，不写库）" if dry_run else ""}')
    counts = {}
    for i, article in enumerate(qs, 1):
        title = article.title or ''
        text = article.ai_summary or (article.content or '')[:800]
        if not title and not text.strip():
            print(f'[{i}/{total}] 跳过（无标题无内容）: {article.url[:60]}')
            continue
        category = service.classify_category(title, text)
        counts[category] = counts.get(category, 0) + 1
        label = article.get_category_display()
        print(f'[{i}/{total}] {category:8s} ({label}) | {title[:40]}')
        if not dry_run:
            article.category = category
            article.save(update_fields=['category', 'updated_at'])
        time.sleep(0.2)  # 轻微限速

    print('\n完成。分布：')
    for code, n in sorted(counts.items(), key=lambda x: -x[1]):
        label = dict(Article.CATEGORY_CHOICES).get(code, code)
        print(f'  {label}: {n}')


if __name__ == '__main__':
    main()
