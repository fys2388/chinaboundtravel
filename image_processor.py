#!/usr/bin/env python3
"""
image_processor.py - 图片占位符处理模块
将文章中的 [Image:xxx] 占位符转换为实际的图片URL

Version: 1.0
"""

import re
import hashlib
from urllib.parse import quote


def generate_image_url(prompt: str, seed: int = None, width: int = 800, height: int = 600) -> str:
    """
    使用 Pollinations.ai 生成图片URL
    
    Args:
        prompt: 图片描述
        seed: 随机种子（用于生成相同图片）
        width: 图片宽度
        height: 图片高度
    
    Returns:
        图片URL
    """
    # 清理提示词
    clean_prompt = prompt.strip()
    
    # 如果没有提供seed，使用prompt的hash作为seed
    if seed is None:
        seed = abs(hash(prompt)) % 100000
    
    # URL编码提示词
    encoded_prompt = quote(clean_prompt)
    
    # 构建URL
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true&seed={seed}"
    
    return url


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
