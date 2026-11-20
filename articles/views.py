"""
文章收藏系统 - 视图
"""

from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
import json
from .models import Article, CollectionTask, WeeklyDigest, Subscriber, EmailSendConfig, PodcastTaskEvent, PodcastAsrAttempt, PodcastAnalysisChunk, PodcastAnalysisRollup
from .serializers import (
    ArticleSerializer, ArticleCreateSerializer, BatchArticleCreateSerializer,
    CollectionTaskSerializer, PodcastTaskEventSerializer, ReconcileSerializer
)
from .podcast import (normalize_xiaoyuzhou_episode_url, PodcastSubmissionService,
                      PodcastAsrClient, safe_event, task_payload)
from .services import ArticleCollectionService
from .weekly_service import WeeklyDigestService
from .subscription_service import SubscriptionService, load_unsubscribe_token
from django.urls import reverse
from django.utils import timezone


class ArticlePagination(PageNumberPagination):
    """文章分页"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ArticleViewSet(viewsets.ModelViewSet):
    """文章视图集"""
    
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    pagination_class = ArticlePagination
    
    def get_queryset(self):
        """获取查询集"""
        queryset = Article.objects.all()
        
        # 平台筛选
        platform = self.request.query_params.get('platform')
        if platform:
            queryset = queryset.filter(platform=platform)
        
        # 搜索
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(content__icontains=search) |
                Q(author__icontains=search)
            )
        
        return queryset.order_by('-collected_at')
    
    @action(detail=False, methods=['post'])
    def collect(self, request):
        """Collect normal articles synchronously and podcasts asynchronously."""
        serializer = ArticleCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        url = serializer.validated_data['url']
        if normalize_xiaoyuzhou_episode_url(url):
            if not request.user.is_authenticated:
                return Response({'success': False, 'message': '收藏播客需要登录。'}, status=status.HTTP_401_UNAUTHORIZED)
            task, message, code = PodcastSubmissionService.submit(url, request.user)
            if task:
                return Response(task_payload(task), status=status.HTTP_202_ACCEPTED)
            return Response({'success': False, 'message': message}, status=code)
        success, message, article = ArticleCollectionService().collect_article(url)
        if success:
            return Response({'success': True, 'message': message, 'article': ArticleSerializer(article).data if article else None}, status=status.HTTP_201_CREATED)
        return Response({'success': False, 'message': message}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def collect_batch(self, request):
        serializer = BatchArticleCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        results = []
        for url in serializer.validated_data['urls']:
            canonical = normalize_xiaoyuzhou_episode_url(url)
            if canonical:
                if not request.user.is_authenticated:
                    results.append({'url': url, 'success': False, 'message': '收藏播客需要登录。', 'status': 401})
                    continue
                task, message, code = PodcastSubmissionService.submit(canonical, request.user)
                results.append({'url': canonical, 'success': bool(task), 'message': message, 'status': code, 'task': task_payload(task) if task else None})
                continue
            success, message, article = ArticleCollectionService().collect_article(url)
            results.append({'url': url, 'success': success, 'message': message, 'article_id': article.id if article else None, 'status': 201 if success else 400})
        return Response({'total': len(results), 'success': sum(1 for result in results if result['success']), 'failed': sum(1 for result in results if not result['success']), 'results': results}, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """获取统计信息"""
        total = Article.objects.count()
        
        # 按平台统计
        platform_stats = Article.objects.values('platform').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # 转换平台显示名称
        platform_display = {}
        for item in platform_stats:
            platform_code = item['platform']
            platform_name = dict(Article.PLATFORM_CHOICES).get(platform_code, platform_code)
            platform_display[platform_name] = item['count']
        
        return Response({
            'total': total,
            'by_platform': platform_display
        })
    
    @action(detail=True, methods=['delete'])
    def delete_article(self, request, pk=None):
        """删除文章"""
        try:
            article = self.get_object()
            if CollectionTask.objects.filter(article=article, task_type='podcast', is_active=True).exists():
                return Response({'success': False, 'message': '播客仍在处理中，不能删除。'}, status=status.HTTP_409_CONFLICT)
            article_title = article.title or "无标题"
            article.delete()
            
            return Response({
                'success': True,
                'message': f'文章 "{article_title}" 已删除'
            }, status=status.HTTP_200_OK)
        except Article.DoesNotExist:
            return Response({
                'success': False,
                'message': '文章不存在'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'])
    def batch_delete(self, request):
        """批量删除文章"""
        article_ids = request.data.get('ids', [])
        
        if not article_ids:
            return Response({
                'success': False,
                'message': '请提供要删除的文章ID列表'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            protected = list(CollectionTask.objects.filter(article_id__in=article_ids, task_type='podcast', is_active=True).values_list('article_id', flat=True))
            if protected:
                return Response({'success': False, 'message': '部分播客仍在处理中，不能删除。', 'protected_ids': protected}, status=status.HTTP_409_CONFLICT)
            deleted_count = Article.objects.filter(id__in=article_ids).count()
            Article.objects.filter(id__in=article_ids).delete()
            return Response({'success': True, 'message': f'成功删除 {deleted_count} 篇文章'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'success': False,
                'message': f'删除失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CollectionTaskViewSet(viewsets.ReadOnlyModelViewSet):
    """Task API. Legacy article tasks remain readable; podcast tasks are private."""
    queryset = CollectionTask.objects.all()
    serializer_class = CollectionTaskSerializer
    pagination_class = ArticlePagination

    def get_queryset(self):
        queryset = CollectionTask.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(Q(task_type='article') | (Q(task_type='podcast', created_by=self.request.user) if self.request.user.is_authenticated else Q(pk__in=[])))
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset.order_by('-created_at')

    def retrieve(self, request, *args, **kwargs):
        task = self.get_object()
        if task.task_type == 'podcast':
            payload = task_payload(task)
            payload['events'] = PodcastTaskEventSerializer(task.podcast_events.all()[:50], many=True).data
            return Response(payload)
        return super().retrieve(request, *args, **kwargs)

    def _podcast_task(self, request, pk):
        try:
            task = CollectionTask.objects.get(pk=pk, task_type='podcast')
        except CollectionTask.DoesNotExist:
            return None
        if not request.user.is_authenticated or not (request.user.is_staff or task.created_by_id == request.user.id):
            return None
        return task

    @action(detail=True, methods=['get'])
    def events(self, request, pk=None):
        task = self._podcast_task(request, pk)
        if not task:
            return Response(status=status.HTTP_404_NOT_FOUND)
        page = self.paginate_queryset(task.podcast_events.all())
        data = PodcastTaskEventSerializer(page if page is not None else task.podcast_events.all(), many=True).data
        return self.get_paginated_response(data) if page is not None else Response(data)

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        task = self._podcast_task(request, pk)
        if not task or task.status != 'failed' or not task.is_retryable or not task.is_active or task.cancel_requested:
            return Response({'detail': '该任务当前不能重试。'}, status=status.HTTP_409_CONFLICT)
        if task.podcast_episode.asr_attempts.filter(external_task_id__gt='').exists():
            stage = 'asr_poll'
        elif task.podcast_episode.transcript_segments.exists():
            stage = 'analysis_chunks'
        else:
            stage = 'metadata'
        # Undispatched AI failures (config/credentials) are retryable: reset the
        # failed analysis items so _analyze re-dispatches only what never succeeded.
        episode = task.podcast_episode
        episode.analysis_chunks.filter(status='failed').update(status='pending', error_code='')
        episode.analysis_rollups.filter(status='failed').update(status='pending', error_code='')
        task.status='pending'; task.stage=stage; task.error_code=''; task.error_message=''; task.next_action=''; task.next_attempt_at=timezone.now(); task.save(update_fields=['status','stage','error_code','error_message','next_action','next_attempt_at','updated_at'])
        safe_event(task, 'manual_retry', '已安排手动重试。', actor=request.user)
        return Response(task_payload(task), status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        task = self._podcast_task(request, pk)
        if not task or not task.is_active or task.status == 'needs_attention':
            return Response({'detail': '该任务当前不能取消。'}, status=status.HTTP_409_CONFLICT)
        task.cancel_requested=True
        if not task.lease_owner:
            task.status='cancelled'; task.stage='cancelled'; task.is_active=False; task.progress_message='本地处理已取消。'
            task.podcast_episode.audio_url=''; task.podcast_episode.save(update_fields=['audio_url'])
        task.save()
        safe_event(task, 'cancel_requested', '已请求停止本地处理；已提交的远端任务可能已经产生费用。', actor=request.user)
        return Response(task_payload(task), status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['post'])
    def reconcile(self, request, pk=None):
        task = self._podcast_task(request, pk)
        if not task or not request.user.is_staff or task.status != 'needs_attention' or task.lease_owner:
            return Response({'detail': '该任务当前不能人工处理。'}, status=status.HTTP_409_CONFLICT)
        serializer = ReconcileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data['action']; episode = task.podcast_episode
        if action == 'abandon_uncertain_submission':
            task.status='failed'; task.stage='failed'; task.is_active=False; task.is_retryable=False; task.next_action=''; task.save()
            episode.audio_url=''; episode.save(update_fields=['audio_url']); safe_event(task, action, '已停止本地处理，外部提交结果仍可能存在，请人工核实费用。', actor=request.user)
            return Response(task_payload(task))
        if action == 'attach_verified_asr':
            external_id=serializer.validated_data.get('external_task_id'); attempt=episode.asr_attempts.filter(status='uncertain',external_task_id='').order_by('-attempt_number').first()
            if not external_id or not attempt:
                return Response({'detail':'提交记录不符合处理条件。'}, status=status.HTTP_409_CONFLICT)
            try: PodcastAsrClient().status(external_id)
            except RuntimeError: return Response({'detail':'无法验证外部任务。'}, status=status.HTTP_409_CONFLICT)
            attempt.external_task_id=external_id; attempt.status='submitted'; attempt.save(); task.status='pending'; task.stage='asr_poll'; task.next_poll_at=timezone.now(); task.save(); safe_event(task, action, '已验证并关联外部转写任务。', actor=request.user)
            return Response(task_payload(task), status=status.HTTP_202_ACCEPTED)
        item_type=serializer.validated_data.get('item_type'); sequence=serializer.validated_data.get('sequence')
        if item_type == 'chunk': item=episode.analysis_chunks.filter(sequence=sequence,status='uncertain').first(); stage='analysis_chunks'
        else: item=episode.analysis_rollups.filter(level=serializer.validated_data.get('level'),sequence=sequence,status='uncertain').first(); stage='analysis_chunks'
        if not item:
            return Response({'detail':'分析记录不符合处理条件。'}, status=status.HTTP_409_CONFLICT)
        item.status='pending'; item.error_code=''; item.completed_at=None; item.save(); task.status='pending'; task.stage=stage; task.save(); safe_event(task, action, '管理员已确认上次分析请求未被接受，已安排重试。', actor=request.user)
        return Response(task_payload(task), status=status.HTTP_202_ACCEPTED)


def changelog_view(request):
    """更新记录页：版本倒序，带相对时间标签。"""
    from .changelog import changelog_entries
    return render(request, 'articles/changelog.html', {'entries': changelog_entries()})


def index(request):
    """首页视图 — 以「最新收藏」为主体，统计仅作辅助信息"""
    from django.utils import timezone
    from datetime import timedelta

    # 统计数据
    total_articles = Article.objects.count()
    week_new_count = Article.objects.filter(
        collected_at__gte=timezone.now() - timedelta(days=7)
    ).count()

    # 获取最新文章，附加阅读时长 / 新鲜度标记
    recent_articles = list(Article.objects.all()[:10])
    for article in recent_articles:
        chars = len(article.content or '')
        if chars >= 300:
            article.reading_minutes = max(1, round(chars / 400))
        else:
            article.reading_minutes = None
        article.is_new = article.collected_at >= timezone.now() - timedelta(days=7)

    context = {
        'total_articles': total_articles,
        'week_new_count': week_new_count,
        'recent_articles': recent_articles,
        'platform_choices': Article.PLATFORM_CHOICES,
    }

    return render(request, 'articles/index.html', context)


def article_list(request):
    """文章列表视图"""
    articles = Article.objects.all()

    # 平台筛选
    platform = request.GET.get('platform')
    if platform:
        articles = articles.filter(platform=platform)

    # 主题分类筛选
    category = request.GET.get('category')
    if category:
        articles = articles.filter(category=category)

    # 搜索
    search = request.GET.get('search')
    if search:
        articles = articles.filter(
            Q(title__icontains=search) |
            Q(content__icontains=search) |
            Q(author__icontains=search)
        )

    articles = articles.order_by('-collected_at')
    paginator = Paginator(articles, 8)
    page = paginator.get_page(request.GET.get('page'))

    context = {
        'articles': page,
        'total_count': paginator.count,
        'platform_choices': Article.PLATFORM_CHOICES,
        'current_platform': platform,
        'category_choices': Article.CATEGORY_CHOICES,
        'current_category': category,
        'search_query': search,
    }

    return render(request, 'articles/list.html', context)


@login_required
def collect_view(request):
    """收藏页面视图 - 需要登录"""
    message = None
    article = None
    
    if request.method == 'POST':
        url = request.POST.get('url')
        if url:
            service = ArticleCollectionService()
            success, msg, art = service.collect_article(url)
            message = {'type': 'success' if success else 'error', 'text': msg}
            article = art
    
    context = {
        'message': message,
        'article': article,
    }
    
    return render(request, 'articles/collect.html', context)


def weekly_digest_list(request):
    """周阅读合集列表视图"""
    service = WeeklyDigestService()
    digests = service.get_all_digests()
    
    context = {
        'digests': digests,
    }
    
    return render(request, 'articles/weekly_list.html', context)


def weekly_digest_detail(request, digest_id):
    """周阅读合集详情视图"""
    service = WeeklyDigestService()
    digest = service.get_digest_by_id(digest_id)
    
    if not digest:
        return render(request, '404.html', status=404)
    
    articles = digest.articles.all().order_by('collected_at')
    
    context = {
        'digest': digest,
        'articles': articles,
    }
    
    return render(request, 'articles/weekly_detail.html', context)


@login_required
def create_weekly_digest(request):
    """手动创建周阅读合集 - 需要登录"""
    if request.method == 'POST':
        service = WeeklyDigestService()
        digest, created = service.create_weekly_digest()
        
        if created:
            message = {'type': 'success', 'text': f'成功创建周阅读合集：{digest.title}'}
        elif digest:
            message = {'type': 'info', 'text': f'该周合集已存在：{digest.title}'}
        else:
            message = {'type': 'error', 'text': '该周暂无收藏文章，无法创建合集'}
        
        context = {
            'message': message,
            'digest': digest,
        }
        
        return render(request, 'articles/weekly_create.html', context)
    
    return render(request, 'articles/weekly_create.html')


def login_view(request):
    """登录视图"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', '/')
            return redirect(next_url)
        else:
            messages.error(request, '用户名或密码错误')
    
    return render(request, 'registration/login.html')


def logout_view(request):
    """登出视图"""
    logout(request)
    return redirect('articles:index')


# ==================== 订阅相关视图 ====================

def get_client_ip(request):
    """获取客户端IP地址"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
    return ip


@require_GET
def get_captcha(request):
    """获取验证码"""
    captcha_id, question = SubscriptionService.generate_captcha()
    return JsonResponse({
        'success': True,
        'captcha_id': captcha_id,
        'question': question
    })


@require_POST
def subscribe(request):
    """订阅邮件:创建 pending 订阅并发确认邮件(double opt-in)"""
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip()
        captcha_id = data.get('captcha_id', '')
        captcha_answer = data.get('captcha_answer', '')

        ip_address = get_client_ip(request)

        success, message, subscriber = SubscriptionService.subscribe(
            email, ip_address, captcha_id, captcha_answer
        )

        payload = {
            'success': success,
            'message': message,
        }
        if success:
            payload['next_url'] = reverse('articles:subscribe_pending')
        return JsonResponse(payload)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '请求数据格式错误'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'订阅失败: {str(e)}'
        }, status=500)


def subscribe_pending_view(request):
    """订阅提交后的"请前往邮箱确认"页面"""
    return render(request, 'articles/subscription/pending.html')


def confirm_subscription_view(request, token):
    """点击邮件中的确认链接 → 激活订阅"""
    success, message, subscriber = SubscriptionService.confirm_subscription(token)
    return render(request, 'articles/subscription/confirmed.html', {
        'success': success,
        'message': message,
        'email': subscriber.email if subscriber else None,
    })


def unsubscribe_view(request, token):
    """退订页面:通过签名 token 还原邮箱"""
    ok, payload = load_unsubscribe_token(token)
    if not ok:
        return render(request, 'articles/unsubscribe.html', {
            'success': False,
            'message': payload,
            'email': None,
        })
    email = payload

    if request.method == 'POST':
        success, message = SubscriptionService.unsubscribe(email)
        return render(request, 'articles/unsubscribe.html', {
            'success': success,
            'message': message,
            'email': email,
        })

    return render(request, 'articles/unsubscribe.html', {
        'email': email,
    })


def unsubscribe_legacy_view(request, email):
    """Deprecated:兼容已发出邮件中携带明文邮箱的退订 URL。新邮件不再使用此路径。"""
    if request.method == 'POST':
        success, message = SubscriptionService.unsubscribe(email)
        return render(request, 'articles/unsubscribe.html', {
            'success': success,
            'message': message,
            'email': email,
        })
    return render(request, 'articles/unsubscribe.html', {'email': email})


# ==================== 订阅管理后台视图 ====================

@login_required
def subscription_admin(request):
    """订阅管理后台首页 - 数据看板"""
    stats = SubscriptionService.get_statistics()
    config = SubscriptionService.get_send_config()
    recent_logs = SubscriptionService.get_send_logs(10)
    
    context = {
        'stats': stats,
        'config': config,
        'recent_logs': recent_logs,
    }
    
    return render(request, 'articles/subscription/dashboard.html', context)


@login_required
def subscription_list(request):
    """订阅者列表"""
    status_filter = request.GET.get('status', '')
    subscribers = SubscriptionService.get_all_subscribers(status_filter if status_filter else None)
    
    context = {
        'subscribers': subscribers,
        'current_status': status_filter,
    }
    
    return render(request, 'articles/subscription/list.html', context)


@login_required
def subscription_send_config(request):
    """发送配置管理"""
    config = SubscriptionService.get_send_config()
    message = None
    
    if request.method == 'POST':
        try:
            weekday = int(request.POST.get('weekday', 6))
            hour = int(request.POST.get('hour', 9))
            minute = int(request.POST.get('minute', 0))
            is_enabled = request.POST.get('is_enabled') == 'on'
            
            # 验证输入
            if not (0 <= weekday <= 6):
                raise ValueError("星期必须在0-6之间")
            if not (0 <= hour <= 23):
                raise ValueError("小时必须在0-23之间")
            if not (0 <= minute <= 59):
                raise ValueError("分钟必须在0-59之间")
            
            config = SubscriptionService.update_send_config(weekday, hour, minute, is_enabled)
            message = {'type': 'success', 'text': '配置保存成功'}
        except ValueError as e:
            message = {'type': 'error', 'text': str(e)}
        except Exception as e:
            message = {'type': 'error', 'text': f'保存失败: {str(e)}'}
    
    context = {
        'config': config,
        'message': message,
        'weekday_choices': EmailSendConfig.WEEKDAY_CHOICES,
    }
    
    return render(request, 'articles/subscription/send_config.html', context)