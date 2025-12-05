"""
文章收藏系统 - 管理后台
"""

from django.contrib import admin
from .models import Article, CollectionTask


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    """文章管理"""
    
    list_display = ['title', 'platform', 'author', 'collected_at']
    list_filter = ['platform', 'collected_at']
    search_fields = ['title', 'author', 'url']
    readonly_fields = ['url_hash', 'collected_at', 'updated_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('url', 'title', 'author', 'platform')
        }),
        ('内容', {
            'fields': ('content', 'tags'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('publish_time', 'collected_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('系统信息', {
            'fields': ('url_hash',),
            'classes': ('collapse',)
        }),
    )


@admin.register(CollectionTask)
class CollectionTaskAdmin(admin.ModelAdmin):
    """收藏任务管理"""
    
    list_display = ['url', 'status', 'article', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['url', 'error_message']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('任务信息', {
            'fields': ('url', 'status', 'article')
        }),
        ('错误信息', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )