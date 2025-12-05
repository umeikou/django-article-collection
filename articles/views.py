"""
文章收藏系统 - 视图
"""

from django.shortcuts import render
from django.db.models import Q, Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from .models import Article, CollectionTask
from .serializers import (
    ArticleSerializer, ArticleCreateSerializer, 
    BatchArticleCreateSerializer, CollectionTaskSerializer
)
from .services import ArticleCollectionService


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
        """收藏单篇文章"""
        serializer = ArticleCreateSerializer(data=request.data)
        if serializer.is_valid():
            url = serializer.validated_data['url']
            
            service = ArticleCollectionService()
            success, message, article = service.collect_article(url)
            
            if success:
                return Response({
                    'success': True,
                    'message': message,
                    'article': ArticleSerializer(article).data if article else None
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'success': False,
                    'message': message
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def collect_batch(self, request):
        """批量收藏文章"""
        serializer = BatchArticleCreateSerializer(data=request.data)
        if serializer.is_valid():
            urls = serializer.validated_data['urls']
            
            service = ArticleCollectionService()
            result = service.collect_batch_articles(urls)
            
            return Response(result, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
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
            deleted_count = Article.objects.filter(id__in=article_ids).count()
            Article.objects.filter(id__in=article_ids).delete()
            
            return Response({
                'success': True,
                'message': f'成功删除 {deleted_count} 篇文章'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'success': False,
                'message': f'删除失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CollectionTaskViewSet(viewsets.ReadOnlyModelViewSet):
    """收藏任务视图集"""
    
    queryset = CollectionTask.objects.all()
    serializer_class = CollectionTaskSerializer
    pagination_class = ArticlePagination
    
    def get_queryset(self):
        """获取查询集"""
        queryset = CollectionTask.objects.all()
        
        # 状态筛选
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-created_at')


def index(request):
    """首页视图"""
    # 获取统计数据
    total_articles = Article.objects.count()
    platform_stats = Article.objects.values('platform').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # 获取最新文章
    recent_articles = Article.objects.all()[:10]
    
    context = {
        'total_articles': total_articles,
        'platform_stats': platform_stats,
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
    
    # 搜索
    search = request.GET.get('search')
    if search:
        articles = articles.filter(
            Q(title__icontains=search) | 
            Q(content__icontains=search) |
            Q(author__icontains=search)
        )
    
    articles = articles.order_by('-collected_at')
    
    context = {
        'articles': articles,
        'platform_choices': Article.PLATFORM_CHOICES,
        'current_platform': platform,
        'search_query': search,
    }
    
    return render(request, 'articles/list.html', context)


def collect_view(request):
    """收藏页面视图"""
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