"""Django admin configuration with podcast credentials and audio URLs redacted."""
from django.contrib import admin
from .models import (Article, CollectionTask, PodcastEpisode, PodcastTaskEvent,
                     PodcastAsrAttempt, PodcastTranscriptSegment, PodcastAnalysisChunk,
                     PodcastAnalysisRollup)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'platform', 'author', 'collected_at']
    list_filter = ['platform', 'collected_at']
    search_fields = ['title', 'author', 'url']
    readonly_fields = ['url_hash', 'collected_at', 'updated_at']


class PodcastTaskEventInline(admin.TabularInline):
    model = PodcastTaskEvent
    extra = 0
    can_delete = False
    readonly_fields = ['created_at', 'level', 'code', 'message', 'actor']
    fields = readonly_fields


@admin.register(CollectionTask)
class CollectionTaskAdmin(admin.ModelAdmin):
    list_display = ['url', 'task_type', 'status', 'stage', 'progress', 'article', 'created_at']
    list_filter = ['task_type', 'status', 'stage', 'created_at']
    search_fields = ['url', 'error_code']
    readonly_fields = ['created_at', 'updated_at', 'lease_owner', 'lease_expires_at', 'heartbeat_at']
    inlines = [PodcastTaskEventInline]


@admin.register(PodcastEpisode)
class PodcastEpisodeAdmin(admin.ModelAdmin):
    list_display = ['canonical_url', 'title', 'podcast_title', 'pay_type', 'is_private', 'article']
    search_fields = ['canonical_url', 'title', 'podcast_title']
    readonly_fields = [field.name for field in PodcastEpisode._meta.fields if field.name != 'audio_url']
    exclude = ['audio_url']


class ReadOnlyPodcastAdmin(admin.ModelAdmin):
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


@admin.register(PodcastAsrAttempt)
class PodcastAsrAttemptAdmin(ReadOnlyPodcastAdmin):
    list_display = ['episode', 'attempt_number', 'input_mode', 'status', 'external_status', 'cost_amount', 'cost_currency']
    exclude = ['external_task_id']


@admin.register(PodcastTranscriptSegment)
class PodcastTranscriptSegmentAdmin(ReadOnlyPodcastAdmin):
    list_display = ['episode', 'sequence', 'start_seconds', 'end_seconds', 'speaker']
    search_fields = ['text']


@admin.register(PodcastAnalysisChunk)
class PodcastAnalysisChunkAdmin(ReadOnlyPodcastAdmin):
    list_display = ['episode', 'sequence', 'status', 'attempt_number', 'completed_at']


@admin.register(PodcastAnalysisRollup)
class PodcastAnalysisRollupAdmin(ReadOnlyPodcastAdmin):
    list_display = ['episode', 'level', 'sequence', 'status', 'attempt_number', 'completed_at']


@admin.register(PodcastTaskEvent)
class PodcastTaskEventAdmin(ReadOnlyPodcastAdmin):
    list_display = ['task', 'created_at', 'level', 'code', 'message']
    list_filter = ['level', 'code']
