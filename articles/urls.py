"""
文章收藏系统 - URL配置
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# API路由
router = DefaultRouter()
router.register(r'articles', views.ArticleViewSet)
router.register(r'tasks', views.CollectionTaskViewSet)

app_name = 'articles'

urlpatterns = [
    # Web页面
    path('', views.index, name='index'),
    path('list/', views.article_list, name='list'),
    path('collect/', views.collect_view, name='collect'),
    
    # API接口
    path('api/', include(router.urls)),
]