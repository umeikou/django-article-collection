# 使用指南

## Web 界面使用

### 1. 访问首页
打开浏览器访问 http://localhost:8000，可以看到：
- 收藏统计信息
- 最新收藏的文章
- 快速操作按钮

### 2. 收藏文章
- 点击"收藏文章"按钮或访问 `/collect/`
- 输入文章链接，点击"收藏"
- 系统会自动解析文章信息并保存

### 3. 浏览文章
- 点击"文章列表"或访问 `/list/`
- 可以按平台筛选文章
- 支持关键词搜索

### 4. 管理后台
- 访问 `/admin/`
- 使用管理员账号登录（用户名: admin, 密码: admin123）
- 可以查看和管理所有文章和收藏任务

## 命令行使用

### 1. 收藏单篇文章
```bash
python3 manage.py collect_article "https://example.com/article"
```

### 2. 批量收藏
```bash
# 创建 URL 文件
echo "https://example1.com" > urls.txt
echo "https://example2.com" >> urls.txt

# 批量收藏
python3 manage.py collect_batch urls.txt
```

### 3. 查看统计
```bash
python3 manage.py show_stats
```

## API 接口使用

### 1. 收藏单篇文章
```bash
curl -X POST http://localhost:8000/api/articles/collect/ \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'
```

### 2. 批量收藏
```bash
curl -X POST http://localhost:8000/api/articles/collect_batch/ \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://example1.com", "https://example2.com"]}'
```

### 3. 获取文章列表
```bash
# 获取所有文章
curl http://localhost:8000/api/articles/

# 按平台筛选
curl http://localhost:8000/api/articles/?platform=weixin

# 搜索文章
curl http://localhost:8000/api/articles/?search=关键词
```

### 4. 获取统计信息
```bash
curl http://localhost:8000/api/articles/statistics/
```

## 支持的平台

| 平台 | 域名 | 解析内容 |
|------|------|----------|
| 微信公众号 | mp.weixin.qq.com | 标题、作者、发布时间、内容 |
| 小红书 | xiaohongshu.com, xhslink.com | 标题、描述 |
| 即刻 | okjike.com, jike.city | 标题、描述 |
| 知乎 | zhihu.com | 标题、作者、内容 |
| 掘金 | juejin.cn | 通用解析 |
| CSDN | csdn.net | 通用解析 |
| 其他 | 任意网站 | 通用解析（meta标签） |

## 常见问题

### Q: 为什么有些文章解析不到内容？
A: 可能的原因：
1. 网站需要登录才能访问
2. 网站有反爬虫机制
3. 网站结构特殊，需要自定义解析规则

### Q: 如何添加新平台支持？
A: 编辑 `articles/services.py`：
1. 在 `detect_platform` 方法中添加域名判断
2. 实现对应的 `_parse_xxx` 方法
3. 在 `models.py` 中添加平台选择项

### Q: 如何自定义解析规则？
A: 修改 `articles/services.py` 中的解析方法，根据网站的HTML结构调整选择器。

### Q: 数据存储在哪里？
A: 默认使用 SQLite 数据库，文件位于项目根目录的 `articles.db`。

## 部署说明

### 开发环境
```bash
./start.sh
```

### 生产环境
1. 修改 `settings.py` 中的生产配置
2. 使用 PostgreSQL 或 MySQL 数据库
3. 配置 Nginx + Gunicorn
4. 设置环境变量和密钥