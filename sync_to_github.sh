#!/bin/bash

echo "🚀 Django文章收藏系统 - GitHub同步脚本"
echo "=========================================="

# 检查是否在正确的目录
if [ ! -f "manage.py" ]; then
    echo "❌ 错误: 请在Django项目根目录运行此脚本"
    exit 1
fi

# 提示用户输入GitHub用户名
read -p "请输入你的GitHub用户名: " GITHUB_USERNAME

if [ -z "$GITHUB_USERNAME" ]; then
    echo "❌ 错误: GitHub用户名不能为空"
    exit 1
fi

echo "📝 配置远程仓库..."

# 检查是否已经配置了远程仓库
if git remote get-url origin 2>/dev/null; then
    echo "⚠️  远程仓库已存在，将更新URL..."
    git remote set-url origin https://github.com/$GITHUB_USERNAME/django-article-collection.git
else
    echo "➕ 添加远程仓库..."
    git remote add origin https://github.com/$GITHUB_USERNAME/django-article-collection.git
fi

echo "🔄 切换到main分支..."
git branch -M main

echo "📤 推送代码到GitHub..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo "✅ 成功！代码已同步到GitHub"
    echo ""
    echo "🌐 访问你的仓库: https://github.com/$GITHUB_USERNAME/django-article-collection"
    echo ""
    echo "📋 后续更新命令:"
    echo "  git add ."
    echo "  git commit -m \"你的提交信息\""
    echo "  git push"
    echo ""
    echo "🔐 建议配置SSH密钥以避免每次输入密码"
    echo "   查看 GITHUB_SETUP.md 了解详细步骤"
else
    echo "❌ 推送失败，请检查:"
    echo "   1. GitHub仓库是否已创建"
    echo "   2. 网络连接是否正常"
    echo "   3. GitHub用户名是否正确"
    echo "   4. 是否有推送权限"
fi