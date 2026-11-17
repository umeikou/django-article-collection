"""
周刊邮件发送服务
支持双通道：阿里云邮件推送 / QQ 邮箱 SMTP，由 EMAIL_BACKEND 环境变量切换

设计约束（必须遵守）：
1) 发给订阅用户的邮件正文中不允许出现任何 emoji。
2) 邮件视觉风格保持简约、留白充足、字号与行高利于阅读。
"""

import os
import re
import sys
import importlib.util
from django.utils import timezone
from django.conf import settings

from .models import Subscriber, WeeklyDigest, EmailSendLog, EmailSendConfig


# Unicode 中常见的 emoji / 符号区段（含 Misc Symbols、Dingbats、Pictographs、Variation Selector 等）。
# 邮件出站前统一过滤一次，作为兜底；prompt 层已要求模型不要输出。
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002600-\U000026FF"
    "\U00002700-\U000027BF"
    "\U0000FE00-\U0000FE0F"
    "\U0001F1E6-\U0001F1FF"
    "]+",
    flags=re.UNICODE,
)


def strip_emoji(text: str) -> str:
    if not text:
        return text
    cleaned = _EMOJI_PATTERN.sub("", text)
    # 去除 emoji 被切掉后留下的成对空格
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned


def _load_module(name: str, path: str):
    """从指定文件路径加载模块，避免两个通道 email_service.py 模块名冲突。"""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法定位模块 {name} @ {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# 简约邮件 HTML 共享样式（内联到每个块）
EMAIL_WRAPPER_BG = "#f7f7f5"
EMAIL_CARD_BG = "#ffffff"
EMAIL_TEXT = "#1f2328"
EMAIL_MUTED = "#6b7280"
EMAIL_BORDER = "#e5e7eb"
EMAIL_ACCENT = "#1f6feb"
SITE_URL = "http://umeikouagent.top"

# 品牌标识：所有外发订阅邮件统一使用该名称
EMAIL_BRAND = "于明浩的阅读列表"


class WeeklyDigestEmailSender:
    """周刊邮件发送器"""

    def __init__(self):
        self.email_service = None
        self.backend = (os.getenv('EMAIL_BACKEND') or getattr(settings, 'EMAIL_BACKEND', 'aliyun_dm') or 'aliyun_dm').strip()
        self._init_email_service()

    def _init_email_service(self):
        """根据 EMAIL_BACKEND 初始化对应通道。失败时 email_service 留 None。"""
        channel_root = os.path.join(settings.BASE_DIR.parent, '通道服务')
        try:
            if self.backend == 'qq_smtp':
                path = os.path.join(channel_root, 'QQMail', 'email_service.py')
                mod = _load_module('qq_email_service', path)
                self.email_service = mod.QQEmailService()
            else:
                # 默认 aliyun_dm
                aliyun_dir = os.path.join(channel_root, 'AliyunDM')
                if aliyun_dir not in sys.path:
                    sys.path.insert(0, aliyun_dir)
                path = os.path.join(aliyun_dir, 'email_service.py')
                mod = _load_module('aliyun_email_service', path)
                self.email_service = mod.AliyunEmailService()
        except Exception as e:
            print(f"初始化邮件服务失败（backend={self.backend}）: {e}")
            self.email_service = None

    def is_available(self):
        """检查邮件服务是否可用"""
        if self.email_service is None:
            return False
        if hasattr(self.email_service, 'is_available'):
            try:
                return bool(self.email_service.is_available())
            except Exception:
                return True
        return True

    # ---------- 内部:HTML 骨架 ----------

    def _unsubscribe_url(self, subscriber_email: str) -> str:
        if not subscriber_email:
            return f"{SITE_URL}/"
        from .subscription_service import make_unsubscribe_token
        token = make_unsubscribe_token(subscriber_email)
        return f"{SITE_URL}/unsubscribe/t/{token}/"

    def _render_layout(self, *, title: str, preheader: str, body_html: str, subscriber_email: str) -> str:
        """简约邮件骨架。所有发给订阅者的 HTML 走这里。"""
        unsubscribe_url = self._unsubscribe_url(subscriber_email)
        title = strip_emoji(title or "")
        preheader = strip_emoji(preheader or "")
        body_html = strip_emoji(body_html or "")
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
</head>
<body style="margin:0;padding:0;background:{EMAIL_WRAPPER_BG};font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei',Helvetica,Arial,sans-serif;color:{EMAIL_TEXT};-webkit-text-size-adjust:100%;">
<span style="display:none!important;visibility:hidden;mso-hide:all;font-size:1px;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;">{preheader}</span>
<table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="background:{EMAIL_WRAPPER_BG};">
<tr><td align="center" style="padding:40px 16px;">
<table width="560" cellpadding="0" cellspacing="0" role="presentation" style="max-width:560px;width:100%;background:{EMAIL_CARD_BG};border:1px solid {EMAIL_BORDER};border-radius:4px;">
<tr><td style="padding:32px 40px 8px 40px;">
<div style="font-size:13px;letter-spacing:0.06em;color:{EMAIL_MUTED};text-transform:uppercase;">{EMAIL_BRAND}</div>
<h1 style="margin:8px 0 0 0;font-size:22px;line-height:1.4;font-weight:600;color:{EMAIL_TEXT};">{title}</h1>
</td></tr>
<tr><td style="padding:24px 40px 32px 40px;font-size:15px;line-height:1.75;color:{EMAIL_TEXT};">
{body_html}
</td></tr>
<tr><td style="padding:20px 40px 28px 40px;border-top:1px solid {EMAIL_BORDER};font-size:12px;line-height:1.7;color:{EMAIL_MUTED};">
<div>此邮件由「{EMAIL_BRAND}」系统发送，您订阅了我们的内容更新。</div>
<div style="margin-top:6px;">如需退订，请点击 <a href="{unsubscribe_url}" style="color:{EMAIL_ACCENT};text-decoration:none;">取消订阅</a>。</div>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""

    # ---------- 周报邮件 ----------

    def generate_weekly_email_html(self, digest, subscriber_email):
        """生成周刊邮件 HTML 内容（简约风、无 emoji）。"""
        articles = digest.articles.all().order_by('collected_at')
        username = subscriber_email.split('@')[0] if subscriber_email else '读者'
        date_range = f"{digest.week_start.strftime('%Y年%m月%d日')} – {digest.week_end.strftime('%Y年%m月%d日')}"
        summary = strip_emoji(digest.summary or '本周收藏了多篇优质文章。')
        summary_html = summary.replace("\n", "<br>")

        # 本周金句区块（仅在有内容时渲染）
        quote_html = ""
        raw_quote = strip_emoji(digest.quote or "").strip()
        if raw_quote:
            quote_html = f"""
<div style="margin:0 0 16px 0;padding:20px 24px;border-left:3px solid {EMAIL_TEXT};background:#fafaf9;">
<div style="font-size:18px;line-height:1.6;font-weight:600;color:{EMAIL_TEXT};letter-spacing:0.01em;">{raw_quote}</div>
<div style="margin-top:10px;font-size:12px;color:{EMAIL_MUTED};letter-spacing:0.04em;text-transform:uppercase;">本周金句</div>
</div>"""

        # 本周数字区块（仅在有内容时渲染）
        stat_html = ""
        raw_stat_number = strip_emoji(digest.stat_number or "").strip()
        raw_stat_context = strip_emoji(digest.stat_context or "").strip()
        if raw_stat_number and raw_stat_context:
            stat_html = f"""
<div style="margin:0 0 32px 0;padding:20px 24px;border:1px solid {EMAIL_BORDER};border-radius:4px;background:#ffffff;">
<div style="font-size:36px;line-height:1.2;font-weight:700;color:{EMAIL_TEXT};letter-spacing:-0.01em;">{raw_stat_number}</div>
<div style="margin-top:8px;font-size:13px;color:{EMAIL_MUTED};line-height:1.6;">{raw_stat_context}</div>
<div style="margin-top:10px;font-size:11px;color:{EMAIL_MUTED};letter-spacing:0.06em;text-transform:uppercase;">本周数字</div>
</div>"""

        items_html = ""
        for i, article in enumerate(articles[:5], 1):
            platform_name = dict(article.PLATFORM_CHOICES).get(article.platform, article.platform)
            title = strip_emoji((article.title or '无标题')[:80])
            items_html += f"""
<tr><td style="padding:14px 0;border-bottom:1px solid {EMAIL_BORDER};">
<div style="font-size:15px;line-height:1.6;"><a href="{article.url}" style="color:{EMAIL_ACCENT};text-decoration:none;">{i}. {title}</a></div>
<div style="margin-top:4px;font-size:12px;color:{EMAIL_MUTED};">来源：{platform_name}</div>
</td></tr>"""

        more_html = ""
        if articles.count() > 5:
            more_html = f'<div style="margin-top:16px;font-size:13px;color:{EMAIL_MUTED};">本周共收藏 {articles.count()} 篇，邮件只展示前 5 篇。</div>'

        body = f"""
<p style="margin:0 0 8px 0;">{username}，您好。</p>
<p style="margin:0 0 24px 0;color:{EMAIL_MUTED};font-size:14px;">{date_range}</p>

{quote_html}

{stat_html}

<div style="margin:0 0 28px 0;">
<div style="font-size:13px;letter-spacing:0.06em;color:{EMAIL_MUTED};text-transform:uppercase;margin-bottom:8px;">本周简报</div>
<div style="font-size:15px;line-height:1.8;color:{EMAIL_TEXT};">{summary_html}</div>
</div>

<div>
<div style="font-size:13px;letter-spacing:0.06em;color:{EMAIL_MUTED};text-transform:uppercase;margin-bottom:4px;">精选文章</div>
<table width="100%" cellpadding="0" cellspacing="0" role="presentation">{items_html}</table>
{more_html}
</div>
"""
        return self._render_layout(
            title=digest.title,
            preheader=raw_quote or f"本周 {articles.count()} 篇精选阅读 · {date_range}",
            body_html=body,
            subscriber_email=subscriber_email,
        )

    def generate_weekly_email_text(self, digest, subscriber_email=None):
        """生成周刊纯文本内容（无 emoji）。"""
        articles = digest.articles.all().order_by('collected_at')
        username = subscriber_email.split('@')[0] if subscriber_email else '读者'
        summary = strip_emoji(digest.summary or '本周收藏了多篇优质文章。')
        raw_quote = strip_emoji(digest.quote or "").strip()

        lines = [
            f"{EMAIL_BRAND} - {strip_emoji(digest.title)}",
            f"{digest.week_start.strftime('%Y年%m月%d日')} - {digest.week_end.strftime('%Y年%m月%d日')}",
            "",
            f"{username}，您好。",
        ]

        if raw_quote:
            lines += [
                "",
                "本周金句",
                raw_quote,
            ]

        raw_stat_number = strip_emoji(digest.stat_number or "").strip()
        raw_stat_context = strip_emoji(digest.stat_context or "").strip()
        if raw_stat_number and raw_stat_context:
            lines += [
                "",
                "本周数字",
                raw_stat_number,
                raw_stat_context,
            ]

        lines += [
            "",
            "本周简报",
            summary,
            "",
            "精选文章",
        ]
        for i, article in enumerate(articles[:5], 1):
            title = strip_emoji((article.title or '无标题')[:80])
            platform_name = dict(article.PLATFORM_CHOICES).get(article.platform, article.platform)
            lines.append(f"{i}. {title}")
            lines.append(f"   来源：{platform_name}")
            lines.append(f"   链接：{article.url}")
            lines.append("")
        if articles.count() > 5:
            lines.append(f"本周共收藏 {articles.count()} 篇，邮件只展示前 5 篇。")
            lines.append("")
        lines += [
            "---",
            f"此邮件由「{EMAIL_BRAND}」系统发送。",
            f"如需退订:{self._unsubscribe_url(subscriber_email)}",
        ]
        return "\n".join(lines)

    # ---------- 欢迎邮件 ----------

    def generate_welcome_email_html(self, subscriber_email: str) -> str:
        username = subscriber_email.split('@')[0] if subscriber_email else '读者'
        section_label = f'font-size:13px;letter-spacing:0.06em;color:{EMAIL_MUTED};text-transform:uppercase;margin:0 0 8px 0;'
        body = f"""
<p style="margin:0 0 16px 0;">{username}，您好。</p>
<p style="margin:0 0 28px 0;">感谢您订阅「{EMAIL_BRAND}」。订阅已经生效，您将在每周固定时间收到一份精选阅读。</p>

<div style="margin:0 0 28px 0;">
<div style="{section_label}">这个网站在做什么</div>
<p style="margin:0 0 12px 0;">这是一份个人维护的阅读清单。我会在日常浏览中,把读到的好内容收藏下来,跨平台汇总——微信公众号、小红书、即刻、知乎、掘金、CSDN 等都覆盖。</p>
<p style="margin:0;">每一篇收藏的文章,都会经过 AI 提炼:抽取核心观点、金句、可以被引用的段落,而不是简单地保留链接。</p>
</div>

<div style="margin:0 0 28px 0;">
<div style="{section_label}">您将收到什么</div>
<p style="margin:0 0 12px 0;">每周一份阅读周报,包含两部分:</p>
<ul style="margin:0;padding-left:20px;line-height:1.9;">
<li><strong style="font-weight:600;">本周阅读简报</strong>:按文章逐篇列出最值得记下的观点,口语化、有冲击力、可被直接引用。</li>
<li><strong style="font-weight:600;">精选文章</strong>:本周收藏的文章列表,附原文链接,可直接点开阅读。</li>
</ul>
</div>

<div style="margin:0 0 28px 0;">
<div style="{section_label}">您可以在站点做什么</div>
<ul style="margin:0;padding-left:20px;line-height:1.9;">
<li>浏览历次周报合集:<a href="{SITE_URL}/weekly/" style="color:{EMAIL_ACCENT};text-decoration:none;">{SITE_URL}/weekly/</a></li>
<li>查看完整文章列表与 AI 摘要:<a href="{SITE_URL}/list/" style="color:{EMAIL_ACCENT};text-decoration:none;">{SITE_URL}/list/</a></li>
</ul>
</div>

<p style="margin:0 0 0 0;color:{EMAIL_MUTED};font-size:13px;">如果某一期内容不再合适,可以随时通过邮件底部链接退订,不会有任何挽留弹窗。</p>
"""
        return self._render_layout(
            title="订阅成功,欢迎",
            preheader=f"您已成功订阅「{EMAIL_BRAND}」,这里是它的使用说明",
            body_html=body,
            subscriber_email=subscriber_email,
        )

    def generate_welcome_email_text(self, subscriber_email: str) -> str:
        username = subscriber_email.split('@')[0] if subscriber_email else '读者'
        return "\n".join([
            f"{username},您好。",
            "",
            f"感谢您订阅「{EMAIL_BRAND}」。订阅已经生效,您将在每周固定时间收到一份精选阅读。",
            "",
            "【这个网站在做什么】",
            "这是一份个人维护的阅读清单。我会在日常浏览中,把读到的好内容收藏下来,",
            "跨平台汇总——微信公众号、小红书、即刻、知乎、掘金、CSDN 等都覆盖。",
            "每一篇收藏的文章,都会经过 AI 提炼:抽取核心观点、金句、可以被引用的段落,",
            "而不是简单地保留链接。",
            "",
            "【您将收到什么】",
            "每周一份阅读周报,包含两部分:",
            "- 本周阅读简报:按文章逐篇列出最值得记下的观点,口语化、有冲击力、可被直接引用",
            "- 精选文章:本周收藏的文章列表,附原文链接,可直接点开阅读",
            "",
            "【您可以在站点做什么】",
            f"- 浏览历次周报合集:{SITE_URL}/weekly/",
            f"- 查看完整文章列表与 AI 摘要:{SITE_URL}/list/",
            "",
            "如果某一期内容不再合适,可以随时通过邮件底部链接退订。",
            "",
            "---",
            f"此邮件由「{EMAIL_BRAND}」系统发送。",
            f"退订入口:{self._unsubscribe_url(subscriber_email)}",
        ])

    def send_welcome_email(self, subscriber):
        """订阅成功后发送欢迎邮件。subscriber 可以是 Subscriber 实例或对象具备 .email 属性。"""
        if not self.is_available():
            return False, "邮件服务不可用"
        email = getattr(subscriber, 'email', None) or str(subscriber)
        if not email:
            return False, "收件人邮箱为空"
        try:
            result = self.email_service.send_single_mail(
                to_address=email,
                subject=f"{EMAIL_BRAND} · 订阅成功，欢迎",
                html_body=self.generate_welcome_email_html(email),
                text_body=self.generate_welcome_email_text(email),
            )
            return result.get('success', False), result.get('message', '未知错误')
        except Exception as e:
            return False, f"发送欢迎邮件失败: {e}"

    # ---------- 确认邮件(double opt-in) ----------

    def _confirm_url(self, subscriber_email: str) -> str:
        from .subscription_service import make_confirm_token
        token = make_confirm_token(subscriber_email)
        return f"{SITE_URL}/subscribe/confirm/{token}/"

    def generate_confirm_email_html(self, subscriber_email: str) -> str:
        username = subscriber_email.split('@')[0] if subscriber_email else '读者'
        confirm_url = self._confirm_url(subscriber_email)
        body = f"""
<p style="margin:0 0 16px 0;">{username},您好。</p>
<p style="margin:0 0 24px 0;">我们收到了使用此邮箱订阅「{EMAIL_BRAND}」的请求。为确认这是您本人的操作,请在 3 天内点击下方按钮完成确认。</p>

<p style="margin:0 0 32px 0;">
<a href="{confirm_url}" style="display:inline-block;background:{EMAIL_TEXT};color:#ffffff;text-decoration:none;padding:12px 24px;border-radius:4px;font-size:15px;font-weight:600;">确认订阅</a>
</p>

<div style="margin:0 0 24px 0;font-size:13px;color:{EMAIL_MUTED};line-height:1.7;">
<div>如果按钮无法点击,请复制以下链接到浏览器打开:</div>
<div style="margin-top:4px;word-break:break-all;color:{EMAIL_ACCENT};">{confirm_url}</div>
</div>

<p style="margin:0;color:{EMAIL_MUTED};font-size:13px;">如果您从未发起过订阅,可以忽略这封邮件——未确认的订阅请求会在 3 天后自动失效,不会再向您发送任何邮件。</p>
"""
        return self._render_layout(
            title="请确认您的订阅",
            preheader=f"3 天内点击链接完成「{EMAIL_BRAND}」的订阅确认",
            body_html=body,
            subscriber_email=subscriber_email,
        )

    def generate_confirm_email_text(self, subscriber_email: str) -> str:
        username = subscriber_email.split('@')[0] if subscriber_email else '读者'
        confirm_url = self._confirm_url(subscriber_email)
        return "\n".join([
            f"{username},您好。",
            "",
            f"我们收到了使用此邮箱订阅「{EMAIL_BRAND}」的请求。",
            "为确认这是您本人的操作,请在 3 天内打开以下链接完成确认:",
            "",
            confirm_url,
            "",
            "如果您从未发起过订阅,可以忽略这封邮件。",
            "未确认的订阅请求会在 3 天后自动失效,不会再向您发送任何邮件。",
            "",
            "---",
            f"此邮件由「{EMAIL_BRAND}」系统发送。",
        ])

    def send_confirm_email(self, subscriber):
        """发送订阅确认邮件(double opt-in 第一步)"""
        if not self.is_available():
            return False, "邮件服务不可用"
        email = getattr(subscriber, 'email', None) or str(subscriber)
        if not email:
            return False, "收件人邮箱为空"
        try:
            result = self.email_service.send_single_mail(
                to_address=email,
                subject=f"{EMAIL_BRAND} · 请确认您的订阅",
                html_body=self.generate_confirm_email_html(email),
                text_body=self.generate_confirm_email_text(email),
            )
            return result.get('success', False), result.get('message', '未知错误')
        except Exception as e:
            return False, f"发送确认邮件失败: {e}"

    # ---------- 周报发送 ----------

    def send_to_subscriber(self, subscriber, digest, use_html=True):
        """
        发送周刊给单个订阅者。默认 HTML + 纯文本双格式，由收件人客户端按支持情况选用。
        """
        if not self.is_available():
            return False, "邮件服务不可用"

        subject = f"{EMAIL_BRAND} · {strip_emoji(digest.title)}"

        if use_html:
            html_body = self.generate_weekly_email_html(digest, subscriber.email)
            text_body = self.generate_weekly_email_text(digest, subscriber.email)
            result = self.email_service.send_single_mail(
                to_address=subscriber.email,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )
        else:
            text_body = self.generate_weekly_email_text(digest, subscriber.email)
            result = self.email_service.send_single_mail(
                to_address=subscriber.email,
                subject=subject,
                text_body=text_body
            )

        return result.get('success', False), result.get('message', '未知错误')
    
    def send_weekly_digest(self, digest=None):
        """发送周刊给所有订阅者"""
        if not self.is_available():
            return {
                'success': False,
                'message': '邮件服务不可用',
                'total': 0,
                'success_count': 0,
                'failed_count': 0
            }
        
        # 获取最新周刊
        if digest is None:
            digest = WeeklyDigest.objects.first()
        
        if not digest:
            return {
                'success': False,
                'message': '没有可发送的周刊',
                'total': 0,
                'success_count': 0,
                'failed_count': 0
            }
        
        # 获取所有活跃订阅者
        subscribers = Subscriber.objects.filter(status='active')
        total = subscribers.count()
        
        if total == 0:
            return {
                'success': False,
                'message': '没有订阅者',
                'total': 0,
                'success_count': 0,
                'failed_count': 0
            }
        
        success_count = 0
        failed_count = 0
        errors = []
        
        for subscriber in subscribers:
            success, message = self.send_to_subscriber(subscriber, digest)
            if success:
                success_count += 1
            else:
                failed_count += 1
                errors.append(f"{subscriber.email}: {message}")
        
        # 记录发送日志
        if success_count == total:
            status = 'success'
        elif success_count > 0:
            status = 'partial'
        else:
            status = 'failed'
        
        EmailSendLog.objects.create(
            weekly_digest=digest,
            total_count=total,
            success_count=success_count,
            failed_count=failed_count,
            status=status,
            error_message='\n'.join(errors) if errors else None
        )
        
        # 更新发送配置的最后发送时间
        config = EmailSendConfig.get_config()
        config.last_sent_at = timezone.now()
        config.save()
        
        return {
            'success': success_count > 0,
            'message': f'发送完成: {success_count}/{total} 成功',
            'total': total,
            'success_count': success_count,
            'failed_count': failed_count,
            'errors': errors
        }


def send_test_email(to_email, digest_id=None):
    """发送测试邮件"""
    sender = WeeklyDigestEmailSender()
    
    if not sender.is_available():
        return {'success': False, 'message': '邮件服务不可用'}
    
    # 获取周刊
    if digest_id:
        digest = WeeklyDigest.objects.filter(id=digest_id).first()
    else:
        digest = WeeklyDigest.objects.first()
    
    if not digest:
        return {'success': False, 'message': '没有可发送的周刊'}
    
    # 创建临时订阅者对象
    class TempSubscriber:
        def __init__(self, email):
            self.email = email
    
    temp_sub = TempSubscriber(to_email)
    success, message = sender.send_to_subscriber(temp_sub, digest)
    
    return {
        'success': success,
        'message': message,
        'digest_title': digest.title
    }
