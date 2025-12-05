"""
文章收藏系统 - 数据模型
"""

from django.db import models
from django.utils import timezone
import hashlib


class Article(models.Model):
    """文章模型"""
    
    PLATFORM_CHOICES = [
        ('weixin', '微信公众号'),
        ('xiaohongshu', '小红书'),
        ('jike', '即刻'),
        ('zhihu', '知乎'),
        ('juejin', '掘金'),
        ('csdn', 'CSDN'),
        ('other', '其他'),
    ]
    
    url = models.URLField(unique=True, verbose_name='文章链接')
    url_hash = models.CharField(max_length=32, unique=True, verbose_name='URL哈希')
    title = models.CharField(max_length=500, blank=True, null=True, verbose_name='标题')
    content = models.TextField(blank=True, null=True, verbose_name='内容')
    author = models.CharField(max_length=200, blank=True, null=True, verbose_name='作者')
    publish_time = models.CharField(max_length=100, blank=True, null=True, verbose_name='发布时间')
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, verbose_name='平台')
    tags = models.CharField(max_length=500, blank=True, null=True, verbose_name='标签')
    collected_at = models.DateTimeField(default=timezone.now, verbose_name='收藏时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '文章'
        verbose_name_plural = '文章'
        ordering = ['-collected_at']
        indexes = [
            models.Index(fields=['url_hash']),
            models.Index(fields=['platform']),
            models.Index(fields=['collected_at']),
        ]
    
    def save(self, *args, **kwargs):
        """保存时自动生成URL哈希"""
        if not self.url_hash:
            self.url_hash = hashlib.md5(self.url.encode()).hexdigest()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title or self.url
    
    @classmethod
    def detect_platform(cls, url):
        """检测文章平台"""
        if "mp.weixin.qq.com" in url:
            return "weixin"
        elif "xiaohongshu.com" in url or "xhslink.com" in url:
            return "xiaohongshu"
        elif "okjike.com" in url or "jike.city" in url:
            return "jike"
        elif "zhihu.com" in url:
            return "zhihu"
        elif "juejin.cn" in url:
            return "juejin"
        elif "csdn.net" in url:
            return "csdn"
        else:
            return "other"


class CollectionTask(models.Model):
    """收藏任务模型"""
    
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('success', '成功'),
        ('failed', '失败'),
    ]
    
    url = models.URLField(verbose_name='文章链接')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    error_message = models.TextField(blank=True, null=True, verbose_name='错误信息')
    article = models.ForeignKey(Article, on_delete=models.CASCADE, blank=True, null=True, verbose_name='关联文章')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '收藏任务'
        verbose_name_plural = '收藏任务'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.url} - {self.get_status_display()}"