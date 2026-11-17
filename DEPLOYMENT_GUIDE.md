# 🚀 Umeikou 的阅读分享 - 部署指南

## 📋 环境说明

### 测试环境 (开发环境)
- **用途**: 开发和测试
- **地址**: http://localhost:8000/
- **数据库**: db.sqlite3
- **服务器**: Django开发服务器
- **配置文件**: settings.py

### 生产环境
- **用途**: 正式上线服务
- **域名**: http://umeikouagent.top
- **数据库**: production.db
- **服务器**: Gunicorn + Nginx
- **配置文件**: settings_production.py

## 🛠️ 快速部署

### 方法一：使用环境管理脚本 (推荐)

```bash
# 启动开发环境
./manage_environments.sh dev

# 部署到生产环境
sudo ./manage_environments.sh deploy

# 查看服务状态
./manage_environments.sh status

# 查看日志
./manage_environments.sh logs
```

### 方法二：手动部署

```bash
# 部署生产环境
sudo bash deploy_production.sh

# 或者分步执行
sudo bash start_production.sh
```

## 📁 文件结构

```
Project/article_collection_django/
├── article_collection_django/
│   ├── settings.py              # 开发环境配置
│   ├── settings_production.py  # 生产环境配置
│   └── wsgi.py                 # WSGI配置
├── manage_environments.sh       # 环境管理脚本
├── deploy_production.sh        # 生产环境部署脚本
├── start_production.sh         # 生产环境启动脚本
├── nginx_config.conf           # Nginx配置文件
├── umeikouagent.service        # Systemd服务文件
├── db.sqlite3                  # 开发环境数据库
├── production.db               # 生产环境数据库
├── staticfiles/                # 生产环境静态文件
└── logs/                       # 日志目录
```

## 🔧 详细部署步骤

### 1. 准备服务器环境

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装必要软件
sudo apt install -y nginx python3-pip python3-venv git

# 安装Python依赖
pip3 install -r requirements.txt
```

### 2. 配置域名解析

确保域名 `umeikouagent.top` 已正确解析到服务器IP地址：

```bash
# 检查域名解析
nslookup umeikouagent.top
ping umeikouagent.top
```

### 3. 执行部署

```bash
# 进入项目目录
cd /usr/Project/article_collection_django

# 执行部署脚本
sudo bash deploy_production.sh
```

### 4. 验证部署

```bash
# 检查服务状态
sudo systemctl status umeikouagent.service
sudo systemctl status nginx

# 测试网站访问
curl -I http://umeikouagent.top
```

## 🌐 Nginx配置详解

### 主要功能
- **反向代理**: 将请求转发给Gunicorn
- **静态文件服务**: 直接提供CSS、JS、图片等静态资源
- **压缩**: 启用Gzip压缩提高传输效率
- **缓存**: 设置静态文件缓存策略
- **安全头**: 添加安全相关的HTTP头

### 配置文件位置
```bash
# Nginx配置文件
/etc/nginx/sites-available/umeikouagent.top
/etc/nginx/sites-enabled/umeikouagent.top

# 日志文件
/var/log/nginx/umeikouagent_access.log
/var/log/nginx/umeikouagent_error.log
```

## ⚙️ Systemd服务管理

### 服务文件
- **主应用**: `/etc/systemd/system/umeikouagent.service`
- **定时任务**: `/etc/systemd/system/weekly-digest.service`
- **定时器**: `/etc/systemd/system/weekly-digest.timer`

### 常用命令
```bash
# 启动服务
sudo systemctl start umeikouagent.service

# 停止服务
sudo systemctl stop umeikouagent.service

# 重启服务
sudo systemctl restart umeikouagent.service

# 查看状态
sudo systemctl status umeikouagent.service

# 查看日志
sudo journalctl -u umeikouagent.service -f

# 启用开机自启
sudo systemctl enable umeikouagent.service
```

## 📊 监控和维护

### 日志文件
```bash
# 应用日志
tail -f /usr/Project/article_collection_django/logs/access.log
tail -f /usr/Project/article_collection_django/logs/error.log

# Nginx日志
tail -f /var/log/nginx/umeikouagent_access.log
tail -f /var/log/nginx/umeikouagent_error.log

# 系统日志
sudo journalctl -u umeikouagent.service -f
```

### 性能监控
```bash
# 检查进程状态
ps aux | grep gunicorn
ps aux | grep nginx

# 检查端口占用
netstat -tlnp | grep :8000
netstat -tlnp | grep :80

# 检查系统资源
htop
df -h
free -h
```

### 数据备份
```bash
# 使用环境管理脚本备份
./manage_environments.sh backup

# 手动备份数据库
cp production.db backups/production_$(date +%Y%m%d_%H%M%S).db

# 备份静态文件
tar -czf backups/staticfiles_$(date +%Y%m%d_%H%M%S).tar.gz staticfiles/
```

## 🔒 安全配置

### SSL证书 (可选)
```bash
# 安装Certbot
sudo apt install certbot python3-certbot-nginx

# 获取SSL证书
sudo certbot --nginx -d umeikouagent.top -d www.umeikouagent.top

# ��动续期
sudo crontab -e
# 添加: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 防火墙配置
```bash
# 启用UFW防火墙
sudo ufw enable

# 允许HTTP和HTTPS
sudo ufw allow 'Nginx Full'

# 允许SSH
sudo ufw allow ssh

# 查看状态
sudo ufw status
```

## 🚨 故障排除

### 常见问题

1. **502 Bad Gateway**
   - 检查Gunicorn服务是否运行
   - 检查端口8000是否被占用
   - 查看应用日志

2. **静态文件404**
   - 执行 `python3 manage.py collectstatic`
   - 检查Nginx静态文件配置
   - 确认文件权限

3. **数据库错误**
   - 检查数据库文件权限
   - 执行数据库迁移
   - 查看应用错误日志

### 调试命令
```bash
# 测试Django配置
python3 manage.py check --settings=article_collection_django.settings_production

# 测试Nginx配置
sudo nginx -t

# 重新加载配置
sudo systemctl reload nginx
sudo systemctl restart umeikouagent.service
```

## 📞 技术支持

### 联系信息
- **项目**: Umeikou 的阅读分享
- **域名**: umeikouagent.top
- **管理员**: umeikou

### 相关文档
- [Django部署文档](https://docs.djangoproject.com/en/stable/howto/deployment/)
- [Nginx配置指南](https://nginx.org/en/docs/)
- [Gunicorn文档](https://docs.gunicorn.org/)

---

*部署指南更新时间: 2025-12-06*