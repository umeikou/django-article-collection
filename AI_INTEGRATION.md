# 通义千问AI集成文档

## 🤖 功能概述

本系统集成了阿里云通义千问大模型，在收藏文章时自动进行智能分析：

1. **提取核心观点**：用一句话概括文章的核心思想（不超过50字）
2. **生成智能摘要**：生成300字左右的文章摘要

## 📋 处理流程

```
用户提交文章URL
    ↓
解析网页内容 (BeautifulSoup)
    ↓
提取文章标题和正文
    ↓
调用通义千问API
    ├─ 提取核心观点（一句话，50字内）
    └─ 生成300字摘要
    ↓
保存到数据库（Article模型）
    ├─ ai_key_point: 核心观点
    └─ ai_summary: 智能摘要
    ↓
展示给用户
```

## 🚀 快速开始

### 1. 获取通义千问API Key

1. 访问 [阿里云DashScope控制台](https://dashscope.console.aliyun.com/)
2. 注册/登录阿里云账号
3. 开通DashScope服务
4. 创建API Key并复制

### 2. 配置环境变量

创建 `.env` 文件（参考 `.env.example`）：

```bash
# 复制示例文件
cp .env.example .env

# 编辑配置文件
vim .env
```

在 `.env` 文件中设置：

```env
# 通义千问API配置
DASHSCOPE_API_KEY=sk-your-api-key-here

# AI功能开关（可选，默认开启）
ENABLE_AI_ANALYSIS=True
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

主要新增依赖：
- `dashscope==1.14.1` - 通义千问Python SDK

### 4. 运行数据库迁移

```bash
python manage.py migrate
```

这会添加两个新字段：
- `ai_key_point` - AI提取的核心观点
- `ai_summary` - AI生成的摘要

### 5. 启动服务

```bash
./start.sh
# 或
python manage.py runserver
```

## 💡 使用方式

### Web界面使用

1. 访问收藏页面：http://localhost:8000/collect/
2. 输入文章URL
3. 点击"智能收藏"
4. 系统会自动：
   - 解析文章内容
   - 调用AI分析
   - 显示核心观点和摘要

### API使用

```bash
# 收藏文章（自动启用AI分析）
curl -X POST http://localhost:8000/api/articles/collect/ \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'

# 响应示例
{
  "success": true,
  "message": "收藏成功",
  "article": {
    "id": 1,
    "title": "文章标题",
    "ai_key_point": "这篇文章的核心观点是...",
    "ai_summary": "本文主要讨论了...（300字摘要）",
    ...
  }
}
```

### 命令行使用

```bash
# 收藏单篇文章
python manage.py collect_article "https://example.com/article"

# 批量收藏（会对每篇文章进行AI分析）
python manage.py collect_batch urls.txt
```

## 🎯 AI分析效果

### 核心观点示例

**原文**：一篇关于Python异步编程的技术文章（3000字）

**AI核心观点**：
> Python的异步编程通过async/await语法实现非阻塞IO操作，显著提升并发性能。

### 摘要示例

**AI生成的300字摘要**：
> 本文深入探讨了Python异步编程的核心概念和实践方法。文章首先介绍了异步编程的基本原理，解释了为什么在处理IO密集型任务时，异步编程能够显著提升性能。接着详细讲解了Python中的async/await语法，以及如何使用asyncio库来实现异步操作。
>
> 文章通过多个实际案例展示了异步编程的应用场景，包括网络请求、文件操作和数据库查询等。作者特别强调了异步编程与多线程、多进程的区别，指出异步编程更适合IO密集型任务，而CPU密集型任务则应该使用多进程。
>
> 最后，文章总结了异步编程的最佳实践，包括如何避免常见的陷阱，如何正确处理异常，以及如何在现有项目中逐步引入异步编程。对于想要提升Python应用性能的开发者来说，这是一篇非常实用的技术指南。

## ⚙️ 配置选项

### AI服务配置

在 `settings.py` 中：

```python
# AI功能开关
ENABLE_AI_ANALYSIS = True  # 全局开关

# API配置
DASHSCOPE_API_KEY = 'your-api-key'
```

### 模型选择

在 `articles/ai_service.py` 中可以调整使用的模型：

```python
# 可选模型：
# - qwen-turbo: 快速，成本低
# - qwen-plus: 平衡性能和成本（推荐）
# - qwen-max: 最强性能，成本高

response = Generation.call(
    model='qwen-plus',  # 修改这里
    ...
)
```

### 内容长度限制

```python
# 在 ai_service.py 中调整
max_content_length = 3000  # 发送给AI的最大内容长度
```

## 🔧 高级功能

### 1. 禁用AI分析

如果某些文章不需要AI分析，可以在代码中控制：

```python
from articles.services import ArticleCollectionService

service = ArticleCollectionService()
success, message, article = service.collect_article(
    url="https://example.com",
    enable_ai=False  # 禁用AI分析
)
```

### 2. 重新分析已收藏的文章

创建管理命令来重新分析：

```bash
python manage.py shell
```

```python
from articles.models import Article
from articles.ai_service import get_ai_service

ai_service = get_ai_service()

# 重新分析所有没有AI摘要的文章
articles = Article.objects.filter(ai_summary__isnull=True)
for article in articles:
    if article.content:
        result = ai_service.analyze_article(
            content=article.content,
            title=article.title
        )
        article.ai_summary = result['summary']
        article.ai_key_point = result['key_point']
        article.save()
        print(f"已分析: {article.title}")
```

### 3. 批量重新分析

```python
# 批量分析前100篇文章
articles = Article.objects.filter(
    ai_summary__isnull=True,
    content__isnull=False
)[:100]

for article in articles:
    result = ai_service.analyze_article(
        content=article.content,
        title=article.title
    )
    article.ai_summary = result['summary']
    article.ai_key_point = result['key_point']
    article.save()
```

## 📊 成本估算

通义千问API按Token计费：

- **qwen-turbo**: ¥0.002/1000 tokens
- **qwen-plus**: ¥0.004/1000 tokens
- **qwen-max**: ¥0.02/1000 tokens

**估算**（使用qwen-plus）：
- 每篇文章分析（3000字内容 + 2次API调用）
- 约消耗 4000-5000 tokens
- 成本约 ¥0.02/篇

**月度成本示例**：
- 每天收藏10篇文章
- 每月300篇
- 月成本约 ¥6

## 🐛 故障排查

### 1. AI功能不工作

检查清单：
- [ ] API Key是否正确设置
- [ ] 网络是否能访问阿里云API
- [ ] 是否有足够的API额度
- [ ] 日志中是否有错误信息

查看日志：
```bash
# 查看Django日志
tail -f logs/django.log

# 或在代码中添加调试
import logging
logger = logging.getLogger(__name__)
logger.info("AI分析开始...")
```

### 2. API调用失败

常见错误：
- `InvalidApiKey`: API Key无效或过期
- `QuotaExceeded`: 超出配额限制
- `NetworkError`: 网络连接问题

解决方案：
```python
# 在 ai_service.py 中查看详细错误
logger.error(f"API调用失败: {response.message}")
```

### 3. 内容过长

如果文章内容超过API限制：
```python
# 自动截断（已实现）
if len(content) > max_content_length:
    content = content[:max_content_length] + "..."
```

## 🔐 安全建议

1. **保护API Key**：
   - 不要将API Key提交到Git
   - 使用环境变量或密钥管理服务
   - 定期轮换API Key

2. **限流控制**：
   - 避免短时间内大量调用
   - 实现请求队列和重试机制

3. **内容过滤**：
   - 过滤敏感内容
   - 验证文章来源

## 📈 性能优化

### 1. 异步处理

对于批量收藏，可以使用Celery异步处理：

```python
# tasks.py
from celery import shared_task

@shared_task
def analyze_article_async(article_id):
    article = Article.objects.get(id=article_id)
    ai_service = get_ai_service()
    result = ai_service.analyze_article(
        content=article.content,
        title=article.title
    )
    article.ai_summary = result['summary']
    article.ai_key_point = result['key_point']
    article.save()
```

### 2. 缓存结果

避免重复分析相同内容：
```python
# 使用Redis缓存
from django.core.cache import cache

cache_key = f"ai_analysis_{article.url_hash}"
cached_result = cache.get(cache_key)
if cached_result:
    return cached_result
```

## 📚 参考资源

- [通义千问官方文档](https://help.aliyun.com/zh/dashscope/)
- [DashScope Python SDK](https://github.com/aliyun/dashscope-sdk-python)
- [API定价](https://dashscope.console.aliyun.com/billing)
- [模型对比](https://help.aliyun.com/zh/dashscope/developer-reference/model-square)

## 🎉 总结

通过集成通义千问AI，文章收藏系统现在能够：

✅ 自动提取文章核心观点  
✅ 生成高质量的300字摘要  
✅ 提升内容可读性和检索效率  
✅ 为用户提供智能化的阅读体验  

AI分析是可选功能，不影响基础的文章收藏功能。即使AI服务不可用，系统仍能正常工作。