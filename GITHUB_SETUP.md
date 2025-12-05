# GitHub 同步指南

## 📋 前置条件

1. 确保你有GitHub账户
2. 已经在本地配置了Git用户信息

## 🚀 同步步骤

### 1. 在GitHub上创建仓库

访问 https://github.com，点击 "New repository"，填写：
- **Repository name**: `django-article-collection`
- **Description**: `🚀 Django-based intelligent article collection system`
- **Visibility**: Public 或 Private
- **不要勾选** "Initialize this repository with a README"

### 2. 添加远程仓库

将下面的命令中的 `YOUR_USERNAME` 替换为你的GitHub用户名：

```bash
git remote add origin https://github.com/YOUR_USERNAME/django-article-collection.git
```

### 3. 推送代码到GitHub

```bash
# 推送到main分支（推荐）
git branch -M main
git push -u origin main

# 或者推送到master分支
git push -u origin master
```

### 4. 验证同步

访问你的GitHub仓库页面，确认代码已经成功上传。

## 🔄 后续更新

当你修改代码后，使用以下命令同步：

```bash
# 添加修改的文件
git add .

# 提交更改
git commit -m "描述你的更改"

# 推送到GitHub
git push
```

## 🔐 SSH密钥配置（推荐）

为了避免每次推送都输入密码，建议配置SSH密钥：

### 1. 生成SSH密钥

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

### 2. 添加到SSH代理

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

### 3. 复制公钥到GitHub

```bash
cat ~/.ssh/id_ed25519.pub
```

将输出的内容复制到GitHub的SSH Keys设置中。

### 4. 更改远程仓库URL为SSH

```bash
git remote set-url origin git@github.com:YOUR_USERNAME/django-article-collection.git
```

## 🏷️ 创建发布版本

当你的项目达到一个稳定版本时，可以创建Release：

1. 在GitHub仓库页面点击 "Releases"
2. 点击 "Create a new release"
3. 填写版本号（如 v1.0.0）和发布说明
4. 点击 "Publish release"

## 📊 项目徽章

你可以在README.md中添加一些徽章来展示项目状态：

```markdown
![Python](https://img.shields.io/badge/python-v3.8+-blue.svg)
![Django](https://img.shields.io/badge/django-v5.2-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![GitHub stars](https://img.shields.io/github/stars/YOUR_USERNAME/django-article-collection.svg)
```

## 🤝 协作开发

如果有其他人要参与开发：

1. 他们需要Fork你的仓库
2. Clone到本地：`git clone https://github.com/THEIR_USERNAME/django-article-collection.git`
3. 创建新分支：`git checkout -b feature/new-feature`
4. 提交更改并推送：`git push origin feature/new-feature`
5. 在GitHub上创建Pull Request

## 🔧 自动化部署

你可以设置GitHub Actions来自动化测试和部署：

创建 `.github/workflows/django.yml` 文件来配置CI/CD流程。