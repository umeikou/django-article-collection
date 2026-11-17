#!/usr/bin/env python
"""
创建favicon图标
"""

from PIL import Image, ImageDraw
import os

def create_favicon():
    """创建圆形favicon"""
    
    # 打开原始头像
    avatar_path = "static/images/avatar.jpg"
    if not os.path.exists(avatar_path):
        print("❌ 头像文件不存在")
        return
    
    # 打开并调整大小
    img = Image.open(avatar_path)
    img = img.resize((32, 32), Image.Resampling.LANCZOS)
    
    # 创建圆形遮罩
    mask = Image.new('L', (32, 32), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, 32, 32), fill=255)
    
    # 创建透明背景
    output = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    output.paste(img, (0, 0))
    output.putalpha(mask)
    
    # 保存为ICO格式
    favicon_path = "static/images/favicon.ico"
    output.save(favicon_path, format='ICO', sizes=[(32, 32)])
    
    print(f"✅ Favicon创建成功: {favicon_path}")
    
    # 同时创建PNG版本
    png_path = "static/images/favicon.png"
    output.save(png_path, format='PNG')
    print(f"✅ PNG版本创建成功: {png_path}")

if __name__ == '__main__':
    create_favicon()