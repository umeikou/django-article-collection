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
    path('changelog/', views.changelog_view, name='changelog'),
    
    # 阅读分享相关
    path('weekly/', views.weekly_digest_list, name='weekly_list'),
    path('weekly/<int:digest_id>/', views.weekly_digest_detail, name='weekly_detail'),
    path('weekly/create/', views.create_weekly_digest, name='weekly_create'),
    
    # 订阅相关
    path('subscribe/captcha/', views.get_captcha, name='get_captcha'),
    path('subscribe/', views.subscribe, name='subscribe'),
    path('subscribe/pending/', views.subscribe_pending_view, name='subscribe_pending'),
    path('subscribe/confirm/<str:token>/', views.confirm_subscription_view, name='subscribe_confirm'),
    path('unsubscribe/t/<str:token>/', views.unsubscribe_view, name='unsubscribe'),
    # Deprecated: 已发出邮件中的明文邮箱 URL,仍可工作,新邮件不再使用
    path('unsubscribe/<str:email>/', views.unsubscribe_legacy_view, name='unsubscribe_legacy'),
    
    # 订阅管理后台（需要登录）
    path('subscription/manage/', views.subscription_admin, name='subscription_admin'),
    path('subscription/manage/list/', views.subscription_list, name='subscription_list'),
    path('subscription/manage/config/', views.subscription_send_config, name='subscription_config'),
    
    # 用户认证
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # API接口
    path('api/', include(router.urls)),
]