# 文章收藏系统 - Django 版本

![Python](https://img.shields.io/badge/python-v3.8+-blue.svg)
![Django](https://img.shields.io/badge/django-v5.2-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![GitHub workflow](https://img.shields.io/github/actions/workflow/status/YOUR_USERNAME/django-article-collection/django.yml)

基于 Django 和 Django REST Framework 构建的多平台文章收藏系统。

## 功能特性

- 🔗 **多平台支持**: 微信公众号、小红书、即刻、知乎、掘金、CSDN等
- 🎙️ **播客收藏**: 支持小宇宙单集，自动转写文字稿并完成全文分析
- 🎯 **智能解析**: 自动提取文章标题、作者、内容等信息
- 🤖 **AI 分析**: 自动生成摘要与主要观点，长文基于全文提炼
- 📚 **每周阅读精选**: 每周自动整合收藏文章，支持邮件订阅推送
- 🔍 **搜索功能**: 支持标题、内容、作者的全文搜索
- 📊 **统计分析**: 收藏数量统计和平台分布
- 🌐 **Web界面**: 友好的用户界面
- 📡 **REST API**: 完整的 RESTful API 接口
- 🛠️ **管理后台**: Django Admin 管理界面

## 快速开始

### 1. 安装依赖

```bash
pip3 install -r requirements.txt
```

### 2. 运行迁移

```bash
python3 manage.py migrate
```

### 3. 创建超级用户（可选）

```bash
python3 manage.py createsuperuser
```

### 4. 启动服务器

```bash
# 使用启动脚本
./start.sh

# 或者直接运行
python3 manage.py runserver 0.0.0.0:8000
```

## 访问地址

- **Web界面**: http://localhost:8000
- **管理后台**: http://localhost:8000/admin
- **API接口**: http://localhost:8000/api/articles/

## API 接口

### 收藏单篇文章

```bash
POST /api/articles/collect/
Content-Type: application/json

{
    "url": "https://mp.weixin.qq.com/s/xxxxx"
}
```

### 批量收藏文章

```bash
POST /api/articles/collect_batch/
Content-Type: application/json

{
    "urls": [
        "https://mp.weixin.qq.com/s/xxxxx",
        "https://www.zhihu.com/question/xxxxx"
    ]
}
```

### 获取文章列表

```bash
GET /api/articles/
GET /api/articles/?platform=weixin
GET /api/articles/?search=关键词
```

### 删除文章

```bash
# 删除单篇文章
DELETE /api/articles/{id}/delete_article/

# 批量删除文章
POST /api/articles/batch_delete/
Content-Type: application/json

{
    "ids": [1, 2, 3]
}
```

### 获取统计信息

```bash
GET /api/articles/statistics/
```

## 项目结构

```
article_collection_django/
├── article_collection_django/  # 项目配置
│   ├── settings.py            # Django 设置
│   └── urls.py               # 主路由配置
├── articles/                 # 文章应用
│   ├── models.py            # 数据模型
│   ├── views.py             # 视图函数
│   ├── serializers.py       # API 序列化器
│   ├── services.py          # 业务逻辑服务
│   ├── admin.py             # 管理后台配置
│   └── urls.py              # 应用路由
├── templates/               # 模板文件
│   └── articles/
├── static/                  # 静态文件
│   ├── css/
│   └── js/
├── manage.py               # Django 管理脚本
├── start.sh               # 启动脚本
└── requirements.txt       # 依赖列表
```

## 支持的平台

- ✅ 微信公众号 (mp.weixin.qq.com)
- ✅ 小红书 (xiaohongshu.com, xhslink.com)
- ✅ 即刻 (okjike.com, jike.city)
- ✅ 知乎 (zhihu.com)
- ✅ 掘金 (juejin.cn)
- ✅ CSDN (csdn.net)
- ✅ 其他网站 (通用解析)

## 技术栈

- **后端**: Django 5.2, Django REST Framework
- **数据库**: SQLite
- **前端**: Bootstrap 5, HTML/CSS/JavaScript
- **解析**: BeautifulSoup4, Requests

## 开发说明

### 添加新平台支持

1. 在 `models.py` 中添加平台选择项
2. 在 `services.py` 中实现对应的解析方法
3. 更新 `detect_platform` 方法

### 自定义解析逻辑

编辑 `articles/services.py` 中的 `ArticleParserService` 类，添加或修改解析方法。

## 部署

### 生产环境设置

1. 修改 `settings.py` 中的 `DEBUG = False`
2. 设置 `ALLOWED_HOSTS`
3. 配置生产数据库（PostgreSQL/MySQL）
4. 使用 Gunicorn + Nginx 部署

### Docker 部署

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

## 更新日志

### v2.2.0 · 2026-11-20
- **新功能：主题分类**
  - 每篇文章和播客收藏后由 AI 自动归类（硅浪 / 商场 / 人间 / 烟火 / 赛场 / 杂记）
  - 文章库新增分类筛选，卡片展示分类标签
  - 首页不再显示平台分布统计

### v2.1.0 · 2026-11-20
- **首页改版**
  - 最新收藏成为页面主体，占满整宽，阅读更聚焦
  - 文章卡片新增预计阅读时长与 7 天内「新」标记
  - AI 摘要默认折叠（展开摘要），核心观点前置展示
  - 支持点击卡片任意位置打开原文
  - 顶部改为「本周新增」视角，平台分布压缩为一行小标签

### v2.0.0 · 2026-11-17
- **新功能：播客收藏**
  - 支持收藏小宇宙单集链接，后台自动完成语音转文字
  - 播客自动生成全文文字稿、摘要和主要观点，像文章一样可搜索、可管理
- **AI 分析升级**
  - 文章观点提取不再受 3,000 字限制，长文基于全文提炼
  - 播客与文章的观点提取风格统一（金句式、口语化、拒绝空话）
  - 观点统一采用「1. / 1.1 / 1.2」编号结构展示

### v1.4.0 · 2026-05-24
- 每周阅读精选新增金句卡片
- 新增周刊统计数据
- 界面与交互体验优化

### v1.3.0 · 2025-12-14
- 邮件订阅系统完善：发送配置、订阅者管理、发送日志

### v1.2.0 · 2025-12-05
- **新功能：AI 智能分析**——收藏文章自动生成摘要与主要观点
- **新功能：每周阅读精选**——每周自动整合收藏文章，支持邮件订阅
- 新增登录与个人资料
- 阅读分享卡片、界面视觉优化

### v1.1.0 · 2025-12-04
- 标题解析增强：自动清理「- 知乎」「- CSDN博客」等网站后缀
- 新增文章删除与批量删除

### v1.0.0 · 2025-12-04
- 正式上线：文章收藏系统
- 支持微信公众号、知乎、小红书等多平台链接收藏
- 完整的 Web 界面、API 与管理后台

## 许可证

MIT License