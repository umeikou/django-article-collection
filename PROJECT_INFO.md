# 文章收藏系统 - Django版本

## 🎯 项目简介

这是一个基于Django开发的智能文章收藏系统，支持多平台文章链接的自动解析和管理。

### ✨ 核心特性

- 🔗 **多平台支持**: 微信公众号、知乎、小红书、即刻、掘金、CSDN等
- 🧠 **智能解析**: 自动提取文章标题、作者、内容摘要
- 🌐 **现代化界面**: 响应式Web界面，支持移动端
- 📡 **RESTful API**: 完整的API接口，支持第三方集成
- 🛠️ **管理后台**: Django Admin管理界面
- 🔍 **搜索功能**: 全文搜索，支持标题、内容、作者
- 📊 **统计分析**: 收藏统计和平台分布
- 🗑️ **批量操作**: 支持批量收藏和删除

## 🏗️ 技术栈

- **后端**: Django 5.2 + Django REST Framework
- **数据库**: SQLite (可扩展到PostgreSQL/MySQL)
- **前端**: Bootstrap 5 + HTML/CSS/JavaScript
- **解析**: BeautifulSoup4 + Requests
- **部署**: Docker + Gunicorn + Nginx (可选)

## 📦 快速开始

### 1. 环境要求

- Python 3.8+
- pip

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 数据库迁移

```bash
python manage.py migrate
```

### 4. 创建管理员账户

```bash
python manage.py createsuperuser
```

### 5. 启动服务

```bash
# 开发环境
python manage.py runserver

# 或使用启动脚本
./start.sh
```

### 6. 访问应用

- **Web界面**: http://localhost:8000
- **管理后台**: http://localhost:8000/admin
- **API文档**: http://localhost:8000/api/articles/

## 🎮 使用方法

### Web界面操作

1. **收藏文章**: 在收藏页面输入文章URL
2. **浏览文章**: 在文章列表查看已收藏的文章
3. **搜索文章**: 使用搜索框查找特定文章
4. **删除文章**: 在文章列表中点击删除按钮

### 命令行操作

```bash
# 收藏单篇文章
python manage.py collect_article "https://example.com/article"

# 批量收藏
python manage.py collect_batch urls.txt

# 查看统计
python manage.py show_stats

# 删除文章
python manage.py delete_article --id 1
```

### API接口

```bash
# 收藏文章
curl -X POST http://localhost:8000/api/articles/collect/ \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'

# 获取文章列表
curl http://localhost:8000/api/articles/

# 删除文章
curl -X DELETE http://localhost:8000/api/articles/1/delete_article/
```

## 📁 项目结构

```
article_collection_django/
├── article_collection_django/  # 项目配置
│   ├── settings.py            # Django设置
│   ├── urls.py               # 主路由
│   └── wsgi.py               # WSGI配置
├── articles/                 # 文章应用
│   ├── models.py            # 数据模型
│   ├── views.py             # 视图函数
│   ├── services.py          # 业务逻辑
│   ├── serializers.py       # API序列化
│   ├── urls.py              # 应用路由
│   ├── admin.py             # 管理后台
│   └── management/          # 管理命令
├── templates/               # 模板文件
├── static/                  # 静态文件
├── requirements.txt         # 依赖列表
├── manage.py               # Django管理脚本
└── README.md               # 项目说明
```

## 🔧 配置说明

### 环境变量

可以通过环境变量配置以下选项：

```bash
export DEBUG=False                    # 调试模式
export SECRET_KEY=your-secret-key     # 密钥
export DATABASE_URL=sqlite:///db.sqlite3  # 数据库URL
```

### 数据库配置

默认使用SQLite，生产环境建议使用PostgreSQL：

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'article_collection',
        'USER': 'your_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## 🐳 Docker部署

```bash
# 构建镜像
docker build -t article-collection .

# 运行容器
docker run -p 8000:8000 article-collection

# 或使用docker-compose
docker-compose up
```

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📝 更新日志

查看 [CHANGELOG.md](CHANGELOG.md) 了解版本更新信息。

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- Django 框架
- Django REST Framework
- Bootstrap 前端框架
- BeautifulSoup 解析库

## 📞 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 Issue
- 发送 Pull Request
- 邮件联系: [your-email@example.com]

---

⭐ 如果这个项目对你有帮助，请给个星标支持！