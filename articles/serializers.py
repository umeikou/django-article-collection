"""文章收藏系统 - 序列化器"""
from rest_framework import serializers
from .models import Article, CollectionTask, PodcastTaskEvent


class ArticleSerializer(serializers.ModelSerializer):
    platform_display = serializers.CharField(source='get_platform_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    class Meta:
        model = Article
        fields = ['id','url','title','content','author','publish_time','platform','platform_display','category','category_display','tags','ai_summary','ai_key_point','collected_at','updated_at']
        read_only_fields = ['id','url_hash','ai_summary','ai_key_point','collected_at','updated_at']


class ArticleCreateSerializer(serializers.Serializer):
    url = serializers.URLField(max_length=2048)
    def validate_url(self, value):
        from .podcast import normalize_xiaoyuzhou_episode_url
        canonical = normalize_xiaoyuzhou_episode_url(value)
        if not canonical and Article.objects.filter(url=value).exists():
            raise serializers.ValidationError('该文章已存在')
        return canonical or value


class BatchArticleCreateSerializer(serializers.Serializer):
    urls = serializers.ListField(child=serializers.URLField(max_length=2048), min_length=1, max_length=100)


class CollectionTaskSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    article_title = serializers.CharField(source='article.title', read_only=True)
    class Meta:
        model = CollectionTask
        fields = ['id','url','status','status_display','error_message','article_title','created_at','updated_at']
        read_only_fields = ['id','created_at','updated_at']


class PodcastTaskEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = PodcastTaskEvent
        fields = ['id','created_at','level','code','message']


class ReconcileSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['attach_verified_asr','abandon_uncertain_submission','confirm_ai_not_dispatched'])
    external_task_id = serializers.RegexField(r'^[A-Za-z0-9_-]{1,128}$', required=False)
    item_type = serializers.ChoiceField(choices=['chunk','rollup'], required=False)
    sequence = serializers.IntegerField(min_value=0, required=False)
    level = serializers.IntegerField(min_value=0, required=False)
