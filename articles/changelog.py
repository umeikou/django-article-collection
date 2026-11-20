# -*- coding: utf-8 -*-
"""站点更新记录（单一数据源）。

发版流程：新增/修改本文件顶部的条目 + 同步更新 README.md 的「更新日志」章节。
条目倒序排列（最新在最前）。released_at 精确到分钟即可。

页面展示规则（release_label）：
- 1 天以内  → 「xx 小时前 / xx 分钟前 / 刚刚」
- 7 天以内  → 「N 天前」
- 7 天以上  → 具体日期（YYYY-MM-DD）
"""
from datetime import datetime

from django.utils import timezone
from django.utils.dateparse import parse_datetime

CHANGELOG = [
    {
        'version': 'v2.2.0',
        'released_at': '2026-11-20 22:10',
        'items': [
            '新功能：主题分类——每篇文章和播客收藏后由 AI 自动归类',
            '六个分类：硅浪（AI 与科技）、商场（商业）、人间（社会人文）、烟火（生活方式）、赛场（体育）、杂记（兜底）',
            '文章库新增分类筛选，卡片展示分类标签',
            '首页不再显示平台分布统计',
        ],
    },
    {
        'version': 'v2.1.0',
        'released_at': '2026-11-20 21:31',
        'items': [
            '首页改版：最新收藏成为页面主体，占满整宽，阅读更聚焦',
            '文章卡片新增预计阅读时长与 7 天内「新」标记',
            'AI 摘要默认折叠（展开摘要），核心观点前置展示',
            '支持点击卡片任意位置打开原文',
            '顶部改为「本周新增」视角，平台分布压缩为一行小标签',
        ],
    },
    {
        'version': 'v2.0.0',
        'released_at': '2026-11-17 15:00',
        'items': [
            '新功能：播客收藏——支持小宇宙单集链接，后台自动完成语音转文字',
            '播客自动生成全文文字稿、摘要和主要观点，像文章一样可搜索、可管理',
            '文章观点提取不再受 3,000 字限制，长文基于全文提炼',
            '播客与文章的观点提取风格统一（金句式、口语化、拒绝空话）',
            '观点统一采用「1. / 1.1 / 1.2」编号结构展示',
        ],
    },
    {
        'version': 'v1.4.0',
        'released_at': '2026-05-24',
        'items': [
            '每周阅读精选新增金句卡片',
            '新增周刊统计数据',
            '界面与交互体验优化',
        ],
    },
    {
        'version': 'v1.3.0',
        'released_at': '2025-12-14',
        'items': [
            '邮件订阅系统完善：发送配置、订阅者管理、发送日志',
        ],
    },
    {
        'version': 'v1.2.0',
        'released_at': '2025-12-05',
        'items': [
            '新功能：AI 智能分析——收藏文章自动生成摘要与主要观点',
            '新功能：每周阅读精选——每周自动整合收藏文章，支持邮件订阅',
            '新增登录与个人资料',
            '阅读分享卡片、界面视觉优化',
        ],
    },
    {
        'version': 'v1.1.0',
        'released_at': '2025-12-04',
        'items': [
            '标题解析增强：自动清理「- 知乎」「- CSDN博客」等网站后缀',
            '新增文章删除与批量删除',
        ],
    },
    {
        'version': 'v1.0.0',
        'released_at': '2025-12-04',
        'items': [
            '正式上线：文章收藏系统',
            '支持微信公众号、知乎、小红书等多平台链接收藏',
            '完整的 Web 界面、API 与管理后台',
        ],
    },
]


def _entries():
    """Changelog entries with timezone-aware datetimes, newest first."""
    entries = []
    for entry in CHANGELOG:
        released = parse_datetime(entry['released_at'])
        if released is None:
            released = datetime.combine(timezone.localdate(), timezone.datetime.min.time())
        if timezone.is_naive(released):
            released = timezone.make_aware(released)
        entries.append({'version': entry['version'], 'released_at': released, 'items': entry['items']})
    return entries


def release_label(released_at, now=None):
    """Human-readable release time per the display rules."""
    now = now or timezone.now()
    delta = now - released_at
    if delta < timezone.timedelta(days=1):
        minutes = int(delta.total_seconds() // 60)
        if minutes < 1:
            return '刚刚'
        if minutes < 60:
            return f'{minutes} 分钟前'
        return f'{int(delta.total_seconds() // 3600)} 小时前'
    if delta < timezone.timedelta(days=7):
        return f'{max(delta.days, 1)} 天前'
    return timezone.localtime(released_at).strftime('%Y-%m-%d')


def changelog_entries():
    """Entries prepared for display: label + concrete date, newest first."""
    result = []
    for entry in _entries():
        result.append({
            'version': entry['version'],
            'label': release_label(entry['released_at']),
            'date': timezone.localtime(entry['released_at']).strftime('%Y-%m-%d'),
            'items': entry['items'],
        })
    return result
