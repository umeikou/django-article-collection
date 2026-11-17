"""
Django settings for article_collection_django project.
"""

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

import os
from dotenv import load_dotenv
load_dotenv(BASE_DIR / '.env')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-your-secret-key-here')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True') == 'True'

# AI功能配置（DeepSeek）
ENABLE_AI_ANALYSIS = os.getenv('ENABLE_AI_ANALYSIS', 'True') == 'True'
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-v4-flash')
DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')

# Podcast worker configuration. Credentials are supplied only through environment variables.
PODCAST_PYTHON = os.getenv('PODCAST_PYTHON', '/usr/bin/python3')
PODCAST_SKILL_DIR = os.getenv('PODCAST_SKILL_DIR', '/root/.kiro/skills/podcast-asr-transcribe/scripts')
PODCAST_FETCH_SCRIPT = os.getenv('PODCAST_FETCH_SCRIPT', f'{PODCAST_SKILL_DIR}/fetch_episode.py')
PODCAST_ASR_SCRIPT = os.getenv('PODCAST_ASR_SCRIPT', f'{PODCAST_SKILL_DIR}/auralwise.py')
PODCAST_METADATA_ADAPTER = str(BASE_DIR / 'articles' / 'podcast_metadata_adapter.py')
PODCAST_CHILD_HOME = os.getenv('PODCAST_CHILD_HOME', '/tmp/podcast-worker-home')
PODCAST_CHILD_PATH = os.getenv('PODCAST_CHILD_PATH', '/usr/local/bin:/usr/bin:/bin')
PODCAST_TEMP_ROOT = os.getenv('PODCAST_TEMP_ROOT', str(BASE_DIR / '.podcast-tmp'))
PODCAST_METADATA_TIMEOUT = int(os.getenv('PODCAST_METADATA_TIMEOUT', '45'))
PODCAST_LEASE_SECONDS = int(os.getenv('PODCAST_LEASE_SECONDS', '120'))
PODCAST_ASR_POLL_SECONDS = int(os.getenv('PODCAST_ASR_POLL_SECONDS', '20'))
PODCAST_AI_INPUT_MAX = int(os.getenv('PODCAST_AI_INPUT_MAX', '2800'))

# 邮件发送通道：aliyun_dm（默认）/ qq_smtp
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'aliyun_dm')

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'articles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'article_collection_django.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'article_collection_django.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / os.getenv('DB_FILE', 'articles.db'),
        'OPTIONS': {
            'init_command': "PRAGMA foreign_keys=1;",
        },
    }
}

# 禁用 SQLite 版本检查
import django.db.backends.sqlite3.base
django.db.backends.sqlite3.base.DatabaseWrapper.check_database_version_supported = lambda self: None


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'zh-hans'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_TZ = True

# 登录设置
LOGIN_URL = '/articles/login/'
LOGIN_REDIRECT_URL = '/articles/'
LOGOUT_REDIRECT_URL = '/articles/'


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
}

# 缓存配置（用于验证码等临时数据存储）
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