"""
文章收藏系统 - 序列化器
"""

from rest_framework import serializers
from .models import Article, CollectionTask


class ArticleSerializer(serializers.ModelSerializer):
    """文章序列化器"""
    
    platform_display = serializers.CharField(source='get_platform_display', read_only=True)
    
    class Meta:
        model = Article
        fields = [
            'id', 'url', 'title', 'content', 'author', 
            'publish_time', 'platform', 'platform_display', 
            'tags', 'collected_at', 'updated_at'
        ]
        read_only_fields = ['id', 'url_hash', 'collected_at', 'updated_at']


class ArticleCreateSerializer(serializers.Serializer):
    """文章创建序列化器"""
    
    url = serializers.URLField()
    
    def validate_url(self, value):
        """验证URL是否已存在"""
        if Article.objects.filter(url=value).exists():
            raise serializers.ValidationError("该文章已存在")
        return value


class BatchArticleCreateSerializer(serializers.Serializer):
    """批量文章创建序列化器"""
    
    urls = serializers.ListField(
        child=serializers.URLField(),
        min_length=1,
        max_length=100
    )


class CollectionTaskSerializer(serializers.ModelSerializer):
    """收藏任务序列化器"""
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    article_title = serializers.CharField(source='article.title', read_only=True)
    
    class Meta:
        model = CollectionTask
        fields = [
            'id', 'url', 'status', 'status_display', 
            'error_message', 'article_title', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']