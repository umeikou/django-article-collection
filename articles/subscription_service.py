"""
邮件订阅服务
"""

import re
import random
import string
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.core.cache import cache
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from .models import Subscriber, EmailSendConfig, EmailSendLog, WeeklyDigest


# 签名命名空间,分开 confirm 和 unsubscribe,防止 token 互用
_CONFIRM_SALT = 'subscriber.confirm'
_UNSUBSCRIBE_SALT = 'subscriber.unsubscribe'

# Token 有效期:确认链接 3 天,退订链接 1 年(用户随时可能想退)
CONFIRM_TOKEN_MAX_AGE = 60 * 60 * 24 * 3
UNSUBSCRIBE_TOKEN_MAX_AGE = 60 * 60 * 24 * 365


def make_confirm_token(email: str) -> str:
    """生成订阅确认 token"""
    return TimestampSigner(salt=_CONFIRM_SALT).sign(email)


def load_confirm_token(token: str):
    """解析订阅确认 token,返回 (ok, email_or_error_message)"""
    try:
        email = TimestampSigner(salt=_CONFIRM_SALT).unsign(token, max_age=CONFIRM_TOKEN_MAX_AGE)
        return True, email
    except SignatureExpired:
        return False, '确认链接已过期,请重新订阅'
    except BadSignature:
        return False, '确认链接无效'


def make_unsubscribe_token(email: str) -> str:
    """生成退订 token"""
    return TimestampSigner(salt=_UNSUBSCRIBE_SALT).sign(email)


def load_unsubscribe_token(token: str):
    """解析退订 token,返回 (ok, email_or_error_message)"""
    try:
        email = TimestampSigner(salt=_UNSUBSCRIBE_SALT).unsign(token, max_age=UNSUBSCRIBE_TOKEN_MAX_AGE)
        return True, email
    except SignatureExpired:
        return False, '退订链接已过期'
    except BadSignature:
        return False, '退订链接无效'


class SubscriptionService:
    """订阅服务"""
    
    CAPTCHA_CACHE_PREFIX = 'captcha_'
    CAPTCHA_EXPIRE_SECONDS = 300  # 5分钟过期
    
    @staticmethod
    def validate_email(email):
        """验证邮箱格式"""
        if not email:
            return False, "邮箱地址不能为空"
        
        # 基本格式验证
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return False, "邮箱格式不正确"
        
        # 长度验证
        if len(email) > 254:
            return False, "邮箱地址过长"
        
        return True, "验证通过"
    
    @staticmethod
    def generate_captcha():
        """生成简单的数学验证码"""
        a = random.randint(1, 20)
        b = random.randint(1, 20)
        operator = random.choice(['+', '-'])
        
        if operator == '+':
            answer = a + b
            question = f"{a} + {b} = ?"
        else:
            # 确保结果为正数
            if a < b:
                a, b = b, a
            answer = a - b
            question = f"{a} - {b} = ?"
        
        # 生成唯一ID
        captcha_id = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        
        # 存储答案到缓存
        cache.set(f'{SubscriptionService.CAPTCHA_CACHE_PREFIX}{captcha_id}', answer, 
                  SubscriptionService.CAPTCHA_EXPIRE_SECONDS)
        
        return captcha_id, question
    
    @staticmethod
    def verify_captcha(captcha_id, user_answer):
        """验证验证码答案"""
        if not captcha_id or not user_answer:
            return False, "请完成人机验证"
        
        try:
            user_answer = int(user_answer)
        except (ValueError, TypeError):
            return False, "验证码答案必须是数字"
        
        cache_key = f'{SubscriptionService.CAPTCHA_CACHE_PREFIX}{captcha_id}'
        correct_answer = cache.get(cache_key)
        
        if correct_answer is None:
            return False, "验证码已过期，请刷新重试"
        
        if user_answer != correct_answer:
            return False, "验证码答案错误"
        
        # 验证成功后删除缓存
        cache.delete(cache_key)
        return True, "验证通过"
    
    @staticmethod
    def subscribe(email, ip_address, captcha_id, captcha_answer):
        """订阅入口:创建/复活 pending 记录,发送确认邮件(double opt-in)"""
        # 验证验证码
        valid, msg = SubscriptionService.verify_captcha(captcha_id, captcha_answer)
        if not valid:
            return False, msg, None

        # 验证邮箱格式
        valid, msg = SubscriptionService.validate_email(email)
        if not valid:
            return False, msg, None

        existing = Subscriber.objects.filter(email=email).first()
        if existing and existing.status == 'active':
            return False, "该邮箱已订阅,无需重复操作", None

        if existing:
            # pending 或 unsubscribed → 重新进入 pending 状态
            existing.status = 'pending'
            existing.ip_address = ip_address
            existing.subscribed_at = timezone.now()
            existing.unsubscribed_at = None
            existing.save()
            subscriber = existing
        else:
            subscriber = Subscriber.objects.create(
                email=email,
                ip_address=ip_address,
                status='pending',
            )

        # 发送确认邮件(失败也返回 success,让用户看到"请查收"页面)
        try:
            from .email_sender import WeeklyDigestEmailSender
            sender = WeeklyDigestEmailSender()
            if sender.is_available():
                sender.send_confirm_email(subscriber)
        except Exception as e:
            print(f"发送确认邮件失败(订阅记录仍为 pending): {e}")

        return True, "确认邮件已发送,请前往邮箱完成激活", subscriber

    @staticmethod
    def confirm_subscription(token):
        """根据确认 token 激活订阅,并发送欢迎邮件"""
        ok, payload = load_confirm_token(token)
        if not ok:
            return False, payload, None

        email = payload
        subscriber = Subscriber.objects.filter(email=email).first()
        if not subscriber:
            return False, "未找到该订阅记录,请重新订阅", None

        if subscriber.status == 'active':
            return True, "您已激活订阅,无需再次确认", subscriber

        subscriber.status = 'active'
        subscriber.subscribed_at = timezone.now()
        subscriber.unsubscribed_at = None
        subscriber.save()

        # 发送欢迎邮件(失败不影响激活结果)
        try:
            from .email_sender import WeeklyDigestEmailSender
            sender = WeeklyDigestEmailSender()
            if sender.is_available():
                sender.send_welcome_email(subscriber)
        except Exception as e:
            print(f"发送欢迎邮件失败(不影响激活): {e}")

        return True, "订阅已激活,感谢您的关注", subscriber

    @staticmethod
    def unsubscribe(email):
        """退订邮件"""
        subscriber = Subscriber.objects.filter(email=email).exclude(status='unsubscribed').first()
        if not subscriber:
            return False, "未找到该订阅"

        subscriber.status = 'unsubscribed'
        subscriber.unsubscribed_at = timezone.now()
        subscriber.save()

        return True, "退订成功"
    
    @staticmethod
    def get_statistics():
        """获取订阅统计数据"""
        total_active = Subscriber.objects.filter(status='active').count()
        total_unsubscribed = Subscriber.objects.filter(status='unsubscribed').count()
        
        # 今日新增
        today = timezone.now().date()
        today_new = Subscriber.objects.filter(
            subscribed_at__date=today,
            status='active'
        ).count()
        
        # 最近7天每日新增
        seven_days_ago = today - timedelta(days=6)
        daily_stats = Subscriber.objects.filter(
            subscribed_at__date__gte=seven_days_ago,
            status='active'
        ).annotate(
            date=TruncDate('subscribed_at')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        # 填充缺失的日期
        daily_data = []
        for i in range(7):
            date = seven_days_ago + timedelta(days=i)
            count = 0
            for stat in daily_stats:
                if stat['date'] == date:
                    count = stat['count']
                    break
            daily_data.append({
                'date': date.strftime('%m-%d'),
                'count': count
            })
        
        return {
            'total_active': total_active,
            'total_unsubscribed': total_unsubscribed,
            'today_new': today_new,
            'daily_data': daily_data
        }
    
    @staticmethod
    def get_all_subscribers(status=None):
        """获取所有订阅者"""
        queryset = Subscriber.objects.all()
        if status:
            queryset = queryset.filter(status=status)
        return queryset.order_by('-subscribed_at')
    
    @staticmethod
    def get_send_config():
        """获取发送配置"""
        return EmailSendConfig.get_config()
    
    @staticmethod
    def update_send_config(weekday, hour, minute, is_enabled=True):
        """更新发送配置"""
        config = EmailSendConfig.get_config()
        config.send_weekday = weekday
        config.send_hour = hour
        config.send_minute = minute
        config.is_enabled = is_enabled
        config.save()
        return config
    
    @staticmethod
    def get_send_logs(limit=20):
        """获取发送日志"""
        return EmailSendLog.objects.all()[:limit]
