"""
生产环境配置
"""

from .settings import *
import os

# 生产环境标识
DEBUG = False

# 允许的主机
ALLOWED_HOSTS = [
    'umeikouagent.top',
    'www.umeikouagent.top',
    '127.0.0.1',
    'localhost',
]

# 安全设置
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# HTTPS设置 (如果使用HTTPS)
# SECURE_SSL_REDIRECT = True
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True

# 静态文件配置
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# 媒体文件配置
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 数据库配置 (生产环境可以使用PostgreSQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'production.db',
    }
}

# 日志配置
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file', 'console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# 缓存配置
# 使用文件缓存而不是 LocMemCache，因为生产环境 gunicorn 有 3 个 worker，
# LocMemCache 是进程本地的，会导致 worker A 生成的验证码在 worker B 验证时找不到。
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': str(BASE_DIR / '.cache'),
        'TIMEOUT': 300,
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        },
    }
}

# 邮件配置 (用于错误报告)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

# 管理员邮箱
ADMINS = [
    ('Umeikou', 'admin@umeikouagent.top'),
]

# 生产 worker 必须使用受控、nginx 可读的脚本副本，不能读取 /root。
PODCAST_SKILL_DIR = os.getenv('PODCAST_SKILL_DIR', '/opt/article-collection/podcast-scripts')
PODCAST_FETCH_SCRIPT = os.getenv('PODCAST_FETCH_SCRIPT', f'{PODCAST_SKILL_DIR}/fetch_episode.py')
PODCAST_ASR_SCRIPT = os.getenv('PODCAST_ASR_SCRIPT', f'{PODCAST_SKILL_DIR}/auralwise.py')
PODCAST_TEMP_ROOT = os.getenv('PODCAST_TEMP_ROOT', '/var/lib/article-collection/podcast-tmp')
PODCAST_CHILD_HOME = os.getenv('PODCAST_CHILD_HOME', '/var/lib/article-collection/podcast-home')

# 时区设置
USE_TZ = True
TIME_ZONE = 'Asia/Shanghai'