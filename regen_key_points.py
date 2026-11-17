# -*- coding: utf-8 -*-
"""一次性脚本：为普通文章用全文重新提取主要观点（ai_key_point）。

- 只重写非播客文章；播客文章由 worker 用新提示词重跑分析
- 新结果为空时不覆盖旧值
- 每篇间隔 0.5 秒，进度逐行输出
"""
import os
import sys
import time

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'article_collection_django.settings_production')
sys.path.insert(0, '/usr/Project/article_collection_django')
django.setup()

from articles.ai_service import DeepSeekAIService  # noqa: E402
from articles.models import Article  # noqa: E402


def main():
    svc = DeepSeekAIService()
    if not svc.is_available():
        print('AI 服务不可用，退出')
        return
    articles = list(Article.objects.exclude(platform='xiaoyuzhou').order_by('id'))
    print(f'共 {len(articles)} 篇普通文章待处理', flush=True)
    done = failed = skipped = 0
    for index, article in enumerate(articles, 1):
        try:
            if len(article.content.strip()) < 50:
                skipped += 1
                print(f'[{index}/{len(articles)}] #{article.id} 内容过短，跳过', flush=True)
                continue
            key_point = svc._extract_key_point(article.content, article.title)
            if key_point:
                Article.objects.filter(pk=article.pk).update(ai_key_point=key_point)
                done += 1
                print(f'[{index}/{len(articles)}] #{article.id} 已更新（{len(article.content)} 字 → {len(key_point)} 字观点）', flush=True)
            else:
                failed += 1
                print(f'[{index}/{len(articles)}] #{article.id} 生成结果为空，保留旧值', flush=True)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f'[{index}/{len(articles)}] #{article.id} 异常：{exc}，保留旧值', flush=True)
        time.sleep(0.5)
    print(f'完成：更新 {done}，空结果 {failed}，跳过 {skipped}', flush=True)


if __name__ == '__main__':
    main()
