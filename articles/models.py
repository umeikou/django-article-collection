"""文章收藏系统 - 数据模型"""
import hashlib
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Article(models.Model):
    PLATFORM_CHOICES = [
        ('weixin', '微信公众号'), ('xiaohongshu', '小红书'), ('jike', '即刻'),
        ('zhihu', '知乎'), ('juejin', '掘金'), ('csdn', 'CSDN'),
        ('xiaoyuzhou', '小宇宙播客'), ('other', '其他'),
    ]
    url = models.URLField(max_length=2048, unique=True, verbose_name='文章链接')
    url_hash = models.CharField(max_length=32, unique=True, verbose_name='URL哈希')
    title = models.CharField(max_length=500, blank=True, null=True, verbose_name='标题')
    content = models.TextField(blank=True, null=True, verbose_name='内容')
    author = models.CharField(max_length=200, blank=True, null=True, verbose_name='作者')
    publish_time = models.CharField(max_length=100, blank=True, null=True, verbose_name='发布时间')
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, verbose_name='平台')
    tags = models.CharField(max_length=500, blank=True, null=True, verbose_name='标签')
    ai_summary = models.TextField(blank=True, null=True, verbose_name='AI摘要(300字)')
    ai_key_point = models.CharField(max_length=500, blank=True, null=True, verbose_name='AI核心观点')
    collected_at = models.DateTimeField(default=timezone.now, verbose_name='收藏时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    class Meta:
        verbose_name = verbose_name_plural = '文章'
        ordering = ['-collected_at']
        indexes = [models.Index(fields=['url_hash']), models.Index(fields=['platform']), models.Index(fields=['collected_at'])]
    def save(self, *args, **kwargs):
        if not self.url_hash:
            self.url_hash = hashlib.md5(self.url.encode()).hexdigest()
        super().save(*args, **kwargs)
    def __str__(self): return self.title or self.url
    @classmethod
    def detect_platform(cls, url):
        if 'mp.weixin.qq.com' in url: return 'weixin'
        if 'xiaoyuzhoufm.com' in url: return 'xiaoyuzhou'
        if 'xiaohongshu.com' in url or 'xhslink.com' in url: return 'xiaohongshu'
        if 'okjike.com' in url or 'jike.city' in url: return 'jike'
        if 'zhihu.com' in url: return 'zhihu'
        if 'juejin.cn' in url: return 'juejin'
        if 'csdn.net' in url: return 'csdn'
        return 'other'


class CollectionTask(models.Model):
    STATUS_CHOICES = [('pending','待处理'),('processing','处理中'),('success','成功'),('failed','失败'),('rejected','已拒绝'),('cancelled','已取消'),('needs_attention','需要人工处理')]
    TASK_TYPES = [('article','文章'), ('podcast','播客')]
    url = models.URLField(max_length=2048, verbose_name='文章链接')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    error_message = models.TextField(blank=True, null=True, verbose_name='错误信息')
    article = models.ForeignKey(Article, on_delete=models.SET_NULL, blank=True, null=True, verbose_name='关联文章')
    task_type = models.CharField(max_length=20, choices=TASK_TYPES, default='article')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='podcast_tasks')
    stage = models.CharField(max_length=40, default='not_applicable')
    progress = models.PositiveSmallIntegerField(default=0)
    progress_message = models.CharField(max_length=200, blank=True)
    error_code = models.CharField(max_length=80, blank=True)
    next_action = models.CharField(max_length=200, blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    work_attempt_number = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    next_poll_at = models.DateTimeField(null=True, blank=True)
    lease_owner = models.CharField(max_length=100, blank=True)
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    heartbeat_at = models.DateTimeField(null=True, blank=True)
    is_retryable = models.BooleanField(default=False)
    cancel_requested = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    podcast_url_key = models.CharField(max_length=2048, null=True, blank=True)
    known_cost_amount = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    known_cost_currency = models.CharField(max_length=8, blank=True)
    external_status = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    class Meta:
        verbose_name = verbose_name_plural = '收藏任务'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['task_type','status','next_attempt_at']), models.Index(fields=['task_type','stage','next_poll_at']), models.Index(fields=['podcast_url_key'])]
        constraints = [models.UniqueConstraint(fields=['podcast_url_key'], condition=Q(task_type='podcast', is_active=True), name='one_active_podcast_task_per_url')]
    def __str__(self): return f'{self.url} - {self.get_status_display()}'


class PodcastEpisode(models.Model):
    task = models.OneToOneField(CollectionTask, on_delete=models.CASCADE, related_name='podcast_episode')
    article = models.OneToOneField(Article, null=True, blank=True, on_delete=models.SET_NULL, related_name='podcast_episode')
    canonical_url = models.URLField(max_length=2048, unique=True)
    episode_id = models.CharField(max_length=200, blank=True)
    title = models.CharField(max_length=500, blank=True)
    podcast_title = models.CharField(max_length=500, blank=True)
    author = models.CharField(max_length=200, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    description = models.TextField(blank=True)
    shownotes = models.TextField(blank=True)
    duration = models.PositiveIntegerField(null=True, blank=True)
    pay_type = models.CharField(max_length=50, blank=True)
    is_private = models.BooleanField(default=False)
    hotwords = models.JSONField(default=list, blank=True)
    language = models.CharField(max_length=20, default='zh')
    transcript_checksum = models.CharField(max_length=64, blank=True)
    asr_summary = models.CharField(max_length=500, blank=True)
    audio_url = models.TextField(blank=True)  # worker-only; never serialize/admin-display


class PodcastTaskEvent(models.Model):
    task = models.ForeignKey(CollectionTask, on_delete=models.CASCADE, related_name='podcast_events')
    created_at = models.DateTimeField(default=timezone.now)
    level = models.CharField(max_length=20, default='info')
    code = models.CharField(max_length=80)
    message = models.CharField(max_length=500)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    class Meta: ordering = ['created_at', 'id']


class PodcastAsrAttempt(models.Model):
    episode = models.ForeignKey(PodcastEpisode, on_delete=models.CASCADE, related_name='asr_attempts')
    attempt_number = models.PositiveIntegerField()
    input_mode = models.CharField(max_length=20, default='audio_url')
    status = models.CharField(max_length=20, default='not_started')
    external_task_id = models.CharField(max_length=128, blank=True)  # private
    external_status = models.CharField(max_length=40, blank=True)
    cost_amount = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    cost_currency = models.CharField(max_length=8, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta: unique_together = [('episode','attempt_number')]


class PodcastTranscriptSegment(models.Model):
    episode = models.ForeignKey(PodcastEpisode, on_delete=models.CASCADE, related_name='transcript_segments')
    sequence = models.PositiveIntegerField()
    start_seconds = models.FloatField(null=True, blank=True)
    end_seconds = models.FloatField(null=True, blank=True)
    speaker = models.CharField(max_length=100, blank=True)
    text = models.TextField()
    class Meta:
        ordering = ['sequence']
        unique_together = [('episode','sequence')]


class PodcastAnalysisChunk(models.Model):
    episode = models.ForeignKey(PodcastEpisode, on_delete=models.CASCADE, related_name='analysis_chunks')
    sequence = models.PositiveIntegerField()
    source_start = models.PositiveIntegerField()
    source_end = models.PositiveIntegerField()
    input_text = models.TextField()
    checksum = models.CharField(max_length=64)
    status = models.CharField(max_length=20, default='pending')
    summary = models.TextField(blank=True)
    key_points = models.JSONField(default=list, blank=True)
    error_code = models.CharField(max_length=80, blank=True)
    dispatch_started_at = models.DateTimeField(null=True, blank=True)
    attempt_number = models.PositiveIntegerField(default=0)
    request_fingerprint = models.CharField(max_length=64, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        ordering = ['sequence']
        unique_together = [('episode','sequence')]


class PodcastAnalysisRollup(models.Model):
    episode = models.ForeignKey(PodcastEpisode, on_delete=models.CASCADE, related_name='analysis_rollups')
    level = models.PositiveIntegerField()
    sequence = models.PositiveIntegerField()
    input_text = models.TextField()
    checksum = models.CharField(max_length=64)
    status = models.CharField(max_length=20, default='pending')
    summary = models.TextField(blank=True)
    key_points = models.JSONField(default=list, blank=True)
    error_code = models.CharField(max_length=80, blank=True)
    dispatch_started_at = models.DateTimeField(null=True, blank=True)
    attempt_number = models.PositiveIntegerField(default=0)
    request_fingerprint = models.CharField(max_length=64, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    class Meta: unique_together = [('episode','level','sequence')]


class WeeklyDigest(models.Model):
    title=models.CharField(max_length=200,verbose_name='合集标题'); week_start=models.DateField(verbose_name='周开始日期'); week_end=models.DateField(verbose_name='周结束日期'); summary=models.TextField(verbose_name='本周阅读总结',help_text='AI生成的200字内总结'); quote=models.TextField(blank=True,null=True,verbose_name='本周金句',help_text='AI从周文章中提取'); stat_number=models.CharField(max_length=50,blank=True,null=True,verbose_name='本周数字'); stat_context=models.CharField(max_length=100,blank=True,null=True,verbose_name='数字背景'); articles=models.ManyToManyField(Article,verbose_name='包含文章'); created_at=models.DateTimeField(default=timezone.now,verbose_name='创建时间'); updated_at=models.DateTimeField(auto_now=True,verbose_name='更新时间')
    class Meta: verbose_name=verbose_name_plural='周阅读合集'; ordering=['-week_start']; unique_together=['week_start','week_end']
    def __str__(self): return f'{self.title} ({self.week_start} - {self.week_end})'
    @property
    def week_year(self): return f'{self.week_start.year}年第{self.week_start.isocalendar()[1]}周'


class Subscriber(models.Model):
    STATUS_CHOICES=[('active','已激活'),('unsubscribed','已退订'),('pending','待确认')]; email=models.EmailField(unique=True,verbose_name='邮箱地址'); ip_address=models.GenericIPAddressField(verbose_name='订阅IP'); status=models.CharField(max_length=20,choices=STATUS_CHOICES,default='active',verbose_name='状态'); subscribed_at=models.DateTimeField(default=timezone.now,verbose_name='订阅时间'); unsubscribed_at=models.DateTimeField(blank=True,null=True,verbose_name='退订时间')
    class Meta: verbose_name=verbose_name_plural='订阅者'; ordering=['-subscribed_at']
    def __str__(self): return f'{self.email} ({self.get_status_display()})'
class EmailSendConfig(models.Model):
    WEEKDAY_CHOICES=[(0,'周一'),(1,'周二'),(2,'周三'),(3,'周四'),(4,'周五'),(5,'周六'),(6,'周日')]; send_weekday=models.IntegerField(choices=WEEKDAY_CHOICES,default=6,verbose_name='发送星期'); send_hour=models.IntegerField(default=9,verbose_name='发送小时(0-23)'); send_minute=models.IntegerField(default=0,verbose_name='发送分钟(0-59)'); is_enabled=models.BooleanField(default=True,verbose_name='是否启用'); last_sent_at=models.DateTimeField(blank=True,null=True,verbose_name='上次发送时间'); created_at=models.DateTimeField(default=timezone.now,verbose_name='创建时间'); updated_at=models.DateTimeField(auto_now=True,verbose_name='更新时间')
    class Meta: verbose_name=verbose_name_plural='邮件发送配置'
    def __str__(self): return f'每{self.get_send_weekday_display()} {self.send_hour:02d}:{self.send_minute:02d} 发送'
    @classmethod
    def get_config(cls): return cls.objects.get_or_create(pk=1)[0]
class EmailSendLog(models.Model):
    STATUS_CHOICES=[('success','成功'),('failed','失败'),('partial','部分成功')]; weekly_digest=models.ForeignKey(WeeklyDigest,on_delete=models.SET_NULL,null=True,verbose_name='周刊'); total_count=models.IntegerField(default=0,verbose_name='总发送数'); success_count=models.IntegerField(default=0,verbose_name='成功数'); failed_count=models.IntegerField(default=0,verbose_name='失败数'); status=models.CharField(max_length=20,choices=STATUS_CHOICES,verbose_name='状态'); error_message=models.TextField(blank=True,null=True,verbose_name='错误信息'); sent_at=models.DateTimeField(default=timezone.now,verbose_name='发送时间')
    class Meta: verbose_name=verbose_name_plural='邮件发送日志'; ordering=['-sent_at']
    def __str__(self): return f'{self.sent_at:%Y-%m-%d %H:%M} - {self.get_status_display()}'
