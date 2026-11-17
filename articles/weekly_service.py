"""
周阅读合集服务
"""

import os
import requests
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q
from .models import Article, WeeklyDigest
from .ai_service import DeepSeekAIService


class WeeklyDigestService:
    """周阅读合集服务"""

    def __init__(self):
        self.ai_service = DeepSeekAIService()
    
    def get_week_range(self, date=None):
        """获取指定日期所在周的开始和结束日期（周一到周日）"""
        if date is None:
            date = timezone.now().date()
        
        # 获取周一
        days_since_monday = date.weekday()
        week_start = date - timedelta(days=days_since_monday)
        
        # 获取周日
        week_end = week_start + timedelta(days=6)
        
        return week_start, week_end
    
    def get_articles_for_week(self, week_start, week_end):
        """获取指定周内收藏的文章"""
        return Article.objects.filter(
            collected_at__date__gte=week_start,
            collected_at__date__lte=week_end
        ).order_by('collected_at')
    
    def generate_weekly_stat(self, articles):
        """从本周文章中提取最反直觉的具体数字，返回 (stat_number, stat_context) 或 (None, None)。"""
        if not articles:
            return None, None

        articles_info = []
        for article in articles:
            info = f"《{article.title or '无标题'}》"
            if article.ai_key_point:
                info += f"\n核心观点: {article.ai_key_point}"
            if article.ai_summary:
                info += f"\n摘要片段: {article.ai_summary[:200]}"
            articles_info.append(info)

        prompt = f"""从下面这{len(articles)}篇文章的内容里，找出一个最反直觉、最让人停下来的具体数字或金额。

{chr(10).join(articles_info)}

严格按以下格式输出，只输出这两行，不要任何其他内容：
第一行：数字本身（如"638元"、"17万人"、"3天"，不超过10个字）
第二行：一句说明这个数字背后含义的话（不超过25个字，口语化，不要任何 emoji）

如果文章里找不到合适的具体数字，输出：
NONE
NONE"""

        try:
            if not self.ai_service.is_available():
                return None, None
            raw = self.ai_service.generate(
                prompt=prompt,
                max_tokens=2048,
                temperature=0.5,
                top_p=0.9,
            )
            if not raw:
                return None, None
            lines = [l.strip() for l in raw.strip().splitlines() if l.strip()]
            if len(lines) >= 2 and lines[0].upper() != 'NONE':
                return lines[0], lines[1]
            return None, None
        except Exception as e:
            print(f"生成本周数字失败: {e}")
            return None, None

    def generate_weekly_quote(self, articles):
        """从本周文章中用 AI 提取一句最具冲击力的金句，作为邮件开篇。"""
        if not articles:
            return None

        articles_info = []
        for article in articles:
            info = f"《{article.title or '无标题'}》"
            if article.ai_key_point:
                info += f"\n核心观点: {article.ai_key_point}"
            if article.ai_summary:
                info += f"\n摘要片段: {article.ai_summary[:200]}"
            articles_info.append(info)

        prompt = f"""从下面这{len(articles)}篇文章的内容里，挑出一句最值得让人停下来想一想的话。

{chr(10).join(articles_info)}

要求：
- 只输出这一句话，不加任何引号、破折号、来源标注、解释或前缀
- 可以是文章原话，也可以是对核心观点的高度凝练改写
- 必须口语化、有画面感或反直觉，让人读完想转发
- 严格控制在 50 字以内
- 绝对禁止输出任何 emoji 或标点装饰符号
- 不要输出任何其他内容，只有这一句话"""

        try:
            if self.ai_service.is_available():
                quote = self.ai_service.generate(
                    prompt=prompt,
                    max_tokens=2048,
                    temperature=0.7,
                    top_p=0.9,
                )
                if quote:
                    return quote.strip()
            return None
        except Exception as e:
            print(f"生成金句失败: {e}")
            return None

    def generate_weekly_summary(self, articles):
        """使用AI生成本周阅读总结"""
        if not articles:
            return "本周暂无收藏文章。"
        
        # 准备文章信息
        articles_info = []
        for article in articles:
            info = f"《{article.title or '无标题'}》"
            if article.ai_key_point:
                info += f" - {article.ai_key_point}"
            elif article.ai_summary:
                info += f" - {article.ai_summary[:100]}..."
            articles_info.append(info)
        
        prompt = f"""
请基于本周收藏的 {len(articles)} 篇文章，生成一份本周阅读简报。

本周文章列表：
{chr(10).join(articles_info)}

请遵循以下原则：

【内容】
- 提炼让人读完会停下来想一想的观点，要金句、要有冲击力、可被引用
- 不要凑数、不要重复、不要强行寻找共同点
- 一篇文章一段，逐篇输出；没有有效观点的文章可以略过

【文字风格】
- 简洁、直白、口语化，像给朋友介绍一本刚看完的书
- 拒绝抽象大词：不要"底层逻辑/赋能/抓手/范式/生态/认知升级"这类空话
- 写人话：能用"老板想让员工多干活"，就别写"组织效能优化"
- 每条观点尽量压在 30 字以内，最多 60 字
- **严禁输出任何 emoji 或装饰性符号**（例如 💡📍💬✅🎉⭐等），输出将用于邮件正文，需要保持纯文本干净

【输出格式】（严格按此结构，不要任何额外引言或总结，不要任何 emoji）

核心洞察（按文章列出）
《文章A标题》
- [一句金句式观点]
- [可选：第二条观点]

《文章B标题》
- [一句金句式观点]
……

一句点评
[针对本周这些文章，写一句接地气的个人感悟，30 字内]
"""
        
        try:
            # 使用AI服务生成总结
            if self.ai_service.is_available():
                summary = self.ai_service.generate(
                    prompt=prompt,
                    max_tokens=4096,
                    temperature=0.6,
                    top_p=0.9,
                )
                if summary:
                    return summary
                return f"本周共收藏了{len(articles)}篇文章，涵盖了多个领域的优质内容。"
            else:
                return f"本周共收藏了{len(articles)}篇文章，涵盖了多个领域的优质内容。"
        except Exception as e:
            print(f"生成周总结失败: {e}")
            return f"本周共收藏了{len(articles)}篇文章，涵盖了多个领域的优质内容。"
    
    def create_weekly_digest(self, week_start=None, week_end=None):
        """创建周阅读合集"""
        if week_start is None or week_end is None:
            # 默认创建上周的合集（周日晚生成）
            today = timezone.now().date()
            if today.weekday() == 6:  # 周日
                week_start, week_end = self.get_week_range(today)
            else:
                # 生成上周的合集
                last_week = today - timedelta(days=7)
                week_start, week_end = self.get_week_range(last_week)
        
        # 检查是否已存在该周的合集
        existing_digest = WeeklyDigest.objects.filter(
            week_start=week_start,
            week_end=week_end
        ).first()
        
        if existing_digest:
            return existing_digest, False
        
        # 获取该周的文章
        articles = self.get_articles_for_week(week_start, week_end)
        
        if not articles:
            return None, False
        
        # 生成AI总结
        summary = self.generate_weekly_summary(articles)

        # 生成本周金句
        quote = self.generate_weekly_quote(articles)

        # 生成本周数字
        stat_number, stat_context = self.generate_weekly_stat(articles)

        # 创建合集
        title = f"{week_start.year}年第{week_start.isocalendar()[1]}周阅读合集"

        digest = WeeklyDigest.objects.create(
            title=title,
            week_start=week_start,
            week_end=week_end,
            summary=summary,
            quote=quote,
            stat_number=stat_number,
            stat_context=stat_context,
        )
        
        # 添加文章
        digest.articles.set(articles)
        
        return digest, True
    
    def get_all_digests(self):
        """获取所有周阅读合集"""
        return WeeklyDigest.objects.all().order_by('-week_start')
    
    def get_digest_by_id(self, digest_id):
        """根据ID获取周阅读合集"""
        try:
            return WeeklyDigest.objects.get(id=digest_id)
        except WeeklyDigest.DoesNotExist:
            return None
    
    def update_digest_summaries(self):
        """更新所有合集的AI总结（用于批量更新）"""
        digests = WeeklyDigest.objects.all()
        updated_count = 0
        
        for digest in digests:
            articles = digest.articles.all()
            if articles:
                new_summary = self.generate_weekly_summary(articles)
                if new_summary != digest.summary:
                    digest.summary = new_summary
                    digest.save()
                    updated_count += 1
        
        return updated_count