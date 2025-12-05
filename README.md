# 文章收藏系统 - Django 版本

![Python](https://img.shields.io/badge/python-v3.8+-blue.svg)
![Django](https://img.shields.io/badge/django-v5.2-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![GitHub workflow](https://img.shields.io/github/actions/workflow/status/YOUR_USERNAME/django-article-collection/django.yml)

基于 Django 和 Django REST Framework 构建的多平台文章收藏系统。

## 功能特性

- 🔗 **多平台支持**: 微信公众号、小红书、即刻、知乎、掘金、CSDN等
- 🎯 **智能解析**: 自动提取文章标题、作者、内容等信息
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

## 许可证

MIT License