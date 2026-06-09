#!/usr/bin/env python3
"""
image_processor.py - 图片占位符处理模块
将文章中的 [Image:xxx] 占位符转换为实际的图片URL

支持的图片生成服务:
1. Pollinations.ai - 默认，免费，无需API密钥
2. Gemini API - 高质量，需要API密钥

Version: 1.1
"""

import re
import hashlib
from urllib.parse import quote


def generate_image_url(prompt: str, seed: int = None, width: int = 800, height: int = 600, service: str = "pollinations") -> str:
    """
    生成图片URL
    
    Args:
        prompt: 图片描述
        seed: 随机种子（用于生成相同图片）
        width: 图片宽度
        height: 图片高度
        service: 图片生成服务，支持 'pollinations' 或 'gemini'
    
    Returns:
        图片URL
    """
    # 清理提示词
    clean_prompt = prompt.strip()
    
    # 如果没有提供seed，使用prompt的hash作为seed
    if seed is None:
        seed = abs(hash(prompt)) % 100000
    
    if service.lower() == "gemini":
        return generate_gemini_url(clean_prompt, width, height)
    else:
        return generate_pollinations_url(clean_prompt, seed, width, height)


def generate_pollinations_url(prompt: str, seed: int, width: int, height: int) -> str:
    """
    使用 Pollinations.ai 生成图片URL（免费，无需API密钥）
    
    Args:
        prompt: 图片描述
        seed: 随机种子
        width: 图片宽度
        height: 图片高度
    
    Returns:
        图片URL
    """
    encoded_prompt = quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true&seed={seed}"
    return url


def generate_gemini_url(prompt: str, width: int = 1024, height: int = 1024) -> str:
    """
    使用 Gemini API 生成图片URL（高质量，需要API密钥）
    
    注意：此函数生成的URL需要在后端或客户端使用API密钥调用
    这里返回的是一个占位符URL，实际使用时需要替换为真实的API调用
    
    Args:
        prompt: 图片描述
        width: 图片宽度（Gemini默认支持512, 1024, 1024+, 最小512x512）
        height: 图片高度
    
    Returns:
        图片URL占位符或CDN URL
    """
    # Gemini 1.5 Pro 支持的图片尺寸:
    # - 512x512
    # - 1024x1024
    # - 1024x1792 (宽x高，适合纵向图片)
    # - 1792x1024 (宽x高，适合横向图片)
    
    # 选择最接近的支持尺寸
    if width >= 1792 and height >= 1024:
        size = "1792x1024"
    elif height >= 1792 and width >= 1024:
        size = "1024x1792"
    elif width >= 1024 and height >= 1024:
        size = "1024x1024"
    else:
        size = "512x512"
    
    # 生成一个标记，用于后续替换为真实的Gemini生成图片
    # 实际使用时需要通过API调用获取真实图片URL
    encoded_prompt = quote(prompt)
    return f"gemini://image?prompt={encoded_prompt}&size={size}"


def replace_image_placeholders(content: str, seed: int = None) -> str:
    """
    将文章中的 [Image:xxx] 占位符替换为实际的图片URL
    
    Args:
        content: 文章内容
        seed: 随机种子（用于生成相同图片）
    
    Returns:
        替换后的文章内容
    """
    # 匹配 [Image:xxx] 格式的占位符
    # 支持格式: [Image:描述] 或 [Image:描述|alt=xxx]
    pattern = r'\[\s*Image\s*:\s*([^\]|]+)(?:\s*\|\s*alt\s*=\s*([^\]]+))?\s*\]'
    
    def replace_match(match):
        prompt = match.group(1).strip()
        alt_text = match.group(2).strip() if match.group(2) else prompt
        
        # 生成图片URL
        image_url = generate_image_url(prompt, seed=seed)
        
        # 返回Markdown图片格式
        return f"![{alt_text}]({image_url})"
    
    # 替换所有匹配
    result = re.sub(pattern, replace_match, content, flags=re.IGNORECASE)
    
    return result


def process_markdown_images(content: str) -> str:
    """
    处理Markdown文章中的图片占位符
    
    Args:
        content: Markdown文章内容
    
    Returns:
        处理后的文章内容（图片占位符已替换为实际图片URL）
    """
    # 使用文章内容的hash作为seed，确保相同内容生成相同图片
    content_hash = abs(hash(content)) % 100000
    
    # 替换图片占位符
    return replace_image_placeholders(content, seed=content_hash)


# 测试函数
def test_image_processor():
    """测试图片处理器"""
    test_content = """
# 测试文章

这是一段测试内容。

[Image:A beautiful sunset over the Great Wall of China]

## 第二部分

[Image:Chinese street food market at night, colorful lanterns, bustling crowd|alt=Chinese night market]

更多内容...
"""
    
    result = process_markdown_images(test_content)
    print("原始内容:")
    print(test_content)
    print("\n处理后内容:")
    print(result)


if __name__ == "__main__":
    test_image_processor()
