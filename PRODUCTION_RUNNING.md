# 生产环境运行状态

## 部署信息

**部署时间**: 2025-12-06 01:43:11 CST  
**服务器**: CentOS Linux  
**项目路径**: /usr/Project/article_collection_django  
**域名**: umeikouagent.top

## 服务状态

### ✅ 主要服务已启动

1. **Django 应用** (umeikouagent.service)
   - 状态: 运行中
   - 端口: 127.0.0.1:8000
   - 进程管理: systemd
   - 应用服务器: Gunicorn (3 workers)
   - 自动重启: 已启用

2. **Nginx 反向代理**
   - 状态: 运行中
   - 端口: 80
   - 配置文件: /etc/nginx/sites-available/umeikouagent.top

3. **定时任务** (weekly-digest.timer)
   - 状态: 已启用
   - 下次执行: 每周日 22:00
   - 功能: 自动生成每周文章摘要

## 24小时运行配置

服务已配置为 24 小时持续运行：

- **自动启动**: 系统启动时自动运行
- **自动重启**: 服务异常时自动重启（10秒后）
- **无限重试**: StartLimitInterval=0
- **健康监控**: systemd 自动监控进程状态

## 访问地址

- **网站**: http://umeikouagent.top
- **管理后台**: http://umeikouagent.top/admin
- **管理员账号**: yumh / Ccc123123

## 管理命令

### 快速管理脚本

```bash
# 使用管理脚本
cd /usr/Project/article_collection_django
./manage_service.sh {start|stop|restart|status|logs|check}
```

### 服务控制

```bash
# 启动服务
systemctl start umeikouagent.service

# 停止服务
systemctl stop umeikouagent.service

# 重启服务
systemctl restart umeikouagent.service

# 查看状态
systemctl status umeikouagent.service

# 查看实时日志
journalctl -u umeikouagent.service -f
```

### Nginx 控制

```bash
# 重启 Nginx
systemctl restart nginx

# 重新加载配置
systemctl reload nginx

# 测试配置
nginx -t
```

### 健康检查

```bash
# 运行健康检查脚本
cd /usr/Project/article_collection_django
./check_service.sh
```

## 日志文件

- **应用访问日志**: /usr/Project/article_collection_django/logs/access.log
- **应用错误日志**: /usr/Project/article_collection_django/logs/error.log
- **Django 日志**: /usr/Project/article_collection_django/logs/django.log
- **Nginx 访问日志**: /var/log/nginx/umeikouagent_access.log
- **Nginx 错误日志**: /var/log/nginx/umeikouagent_error.log
- **系统日志**: journalctl -u umeikouagent.service

## 数据库

- **类型**: SQLite3
- **文件**: /usr/Project/article_collection_django/production.db
- **备份建议**: 定期备份数据库文件

## 静态文件

- **静态文件目录**: /usr/Project/article_collection_django/staticfiles/
- **媒体文件目录**: /usr/Project/article_collection_django/media/

## 定时任务

### 每周摘要生成

- **服务**: weekly-digest.service
- **定时器**: weekly-digest.timer
- **执行时间**: 每周日 22:00
- **查看状态**: `systemctl list-timers weekly-digest.timer`

## 监控建议

1. **定期检查服务状态**
   ```bash
   ./check_service.sh
   ```

2. **监控日志**
   ```bash
   tail -f logs/error.log
   ```

3. **检查磁盘空间**
   ```bash
   df -h /usr/Project/article_collection_django
   ```

4. **查看系统资源**
   ```bash
   systemctl status umeikouagent.service
   ```

## 故障排查

### 服务无法启动

```bash
# 查看详细错误
journalctl -u umeikouagent.service -n 50

# 检查配置文件
cat /etc/systemd/system/umeikouagent.service

# 手动测试启动
cd /usr/Project/article_collection_django
gunicorn --bind 127.0.0.1:8000 article_collection_django.wsgi:application
```

### 网站无法访问

```bash
# 检查端口监听
netstat -tlnp | grep -E ':(8000|80)'

# 测试本地访问
curl -I http://127.0.0.1:8000

# 检查 Nginx 配置
nginx -t
```

### 性能问题

```bash
# 查看进程资源使用
ps aux | grep gunicorn

# 调整 worker 数量（编辑 service 文件）
vim /etc/systemd/system/umeikouagent.service
# 修改 --workers 参数
```

## 更新部署

```bash
# 1. 拉取最新代码
cd /usr/Project/article_collection_django
git pull

# 2. 安装依赖
pip3 install -r requirements.txt

# 3. 数据库迁移
python3 manage.py migrate --settings=article_collection_django.settings_production

# 4. 收集静态文件
python3 manage.py collectstatic --noinput --settings=article_collection_django.settings_production

# 5. 重启服务
systemctl restart umeikouagent.service
systemctl reload nginx
```

## 安全建议

1. 定期更新系统和依赖包
2. 配置防火墙规则
3. 启用 HTTPS（配置 SSL 证书）
4. 定期备份数据库
5. 监控异常访问日志

## 性能优化

- **Worker 数量**: 当前 3 个（可根据 CPU 核心数调整）
- **静态文件**: 已启用 Nginx 缓存（30天）
- **Gzip 压缩**: 已启用
- **数据库**: 考虑迁移到 PostgreSQL（生产环境推荐）

## 联系信息

- **项目**: Umeikou 的阅读分享
- **管理员**: yumh
- **邮箱**: admin@umeikouagent.top
