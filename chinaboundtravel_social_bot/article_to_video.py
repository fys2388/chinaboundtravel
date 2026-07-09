#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hugo 文章转 YouTube 短视频
读取 Hugo markdown 文章 -> 提取内容 -> TTS 旁白 -> 图片+音频合成视频
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

try:
    import requests
except ImportError:
    print("[错误] 需要安装 requests 库: pip install requests")
    sys.exit(1)

try:
    import edge_tts
except ImportError:
    print("[错误] 需要安装 edge-tts 库: pip install edge-tts")
    sys.exit(1)


# --- 配置 ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(SCRIPT_DIR, "..", "content", "posts")
VIDEO_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "..", "static", "videos")
TTS_VOICE = "en-US-JennyNeural"
TARGET_WORD_COUNT = 150  # 目标旁白约 150 词 (~60 秒)
POLLINATIONS_BASE = "https://image.pollinations.ai/prompt"


# ========== Hugo frontmatter 解析 ==========

def parse_frontmatter(text):
    """解析 Hugo markdown 的 frontmatter，返回 (metadata_dict, body_str)"""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
    if not match:
        return {}, text

    raw_fm = match.group(1)
    body = match.group(2).strip()

    meta = {}
    for line in raw_fm.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()

        # 处理带引号的字符串
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        # 处理布尔值
        elif value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        # 处理数组格式 [a, b, c]
        elif value.startswith("[") and value.endswith("]"):
            items = value[1:-1].split(",")
            value = [item.strip().strip('"\'') for item in items if item.strip()]

        meta[key] = value

    return meta, body


def extract_sections(body):
    """从 markdown body 提取段落和标题"""
    # 移除图片语法
    body = re.sub(r"!\[.*?\]\(.*?\)", "", body)
    # 移除链接但保留文字
    body = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", body)
    # 移除 shortcode {{ ... }}
    body = re.sub(r"\{\{.*?\}\}", "", body)
    # 按空行分段
    paragraphs = re.split(r"\n\s*\n", body)

    sections = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        # 检查是否是标题行
        heading_match = re.match(r"^(#{1,6})\s+(.*)", p)
        if heading_match:
            sections.append({"type": "heading", "text": heading_match.group(2).strip()})
        else:
            # 清理 markdown 格式
            clean = re.sub(r"[#*`\[\]>|_-]", "", p)
            clean = re.sub(r"\s+", " ", clean).strip()
            if len(clean) > 20:  # 过滤太短的段落
                sections.append({"type": "paragraph", "text": clean})

    return sections


# ========== 旁白脚本生成 ==========

def generate_narration(title, description, sections):
    """从文章内容生成约 150 词的自然旁白"""
    # 收集前几段正文
    body_paragraphs = [s["text"] for s in sections if s["type"] == "paragraph"]

    # 取前 3-4 段，限制总词数
    selected = []
    word_count = 0
    for p in body_paragraphs:
        words = p.split()
        selected.append(p)
        word_count += len(words)
        if word_count >= 200 or len(selected) >= 4:
            break

    if not selected:
        # 如果没有有效段落，使用描述
        selected = [description or title]

    # 拼接并截断到目标词数附近
    combined = " ".join(selected)
    words = combined.split()
    if len(words) > TARGET_WORD_COUNT + 30:
        words = words[:TARGET_WORD_COUNT + 30]
        combined = " ".join(words)

    # 添加开头和结尾
    intro = f"Discover {title}. "
    cta = "Subscribe to China Bound Travel for more amazing China travel guides. See you on the next adventure!"

    narration = f"{intro}{combined}. {cta}"

    # 清理多余空格
    narration = re.sub(r"\s+", " ", narration).strip()

    return narration


# ========== TTS 音频生成 ==========

def generate_tts_audio(text, output_path):
    """使用 Edge TTS 生成语音"""
    print(f"[TTS] 正在生成语音 ({len(text.split())} 词)...")
    try:
        communicate = edge_tts.Communicate(text, TTS_VOICE)
        communicate.save(output_path)
        print(f"[OK] 语音已保存: {output_path}")
        return True
    except Exception as e:
        print(f"[错误] TTS 生成失败: {e}")
        return False


# ========== 图片处理 ==========

def download_image(url, output_path):
    """下载封面图片"""
    print(f"[图片] 正在下载: {url[:80]}...")
    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(resp.content)
        print(f"[OK] 图片已保存: {output_path}")
        return True
    except Exception as e:
        print(f"[警告] 图片下载失败: {e}")
        return False


def generate_cover_image(topic, output_path):
    """使用 Pollinations.ai 生成封面图片"""
    prompt = f"travel photography of {topic}, no people, no faces, no portraits, cinematic, high quality, 4k"
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"{POLLINATIONS_BASE}/{encoded_prompt}?width=1280&height=720&nologo=true"

    print(f"[图片] 正在生成 AI 封面 (主题: {topic})...")
    return download_image(url, output_path)


def create_thumbnail(image_path, thumb_path):
    """从封面图创建缩略图 (1280x720)"""
    if not os.path.exists(image_path):
        print(f"[警告] 源图片不存在，无法创建缩略图: {image_path}")
        return False

    # 尝试用 ffmpeg 缩放
    try:
        cmd = [
            "ffmpeg", "-y", "-i", image_path,
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:black",
            "-q:v", "2", thumb_path
        ]
        subprocess.run(cmd, capture_output=True, check=True, timeout=30)
        print(f"[OK] 缩略图已创建: {thumb_path}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        # ffmpeg 不可用，直接复制
        shutil.copy2(image_path, thumb_path)
        print(f"[OK] 缩略图已复制: {thumb_path}")
        return True


# ========== 视频合成 ==========

def create_video_ffmpeg(image_path, audio_path, output_path):
    """使用 ffmpeg 合成视频（图片+音频）"""
    print("[视频] 正在使用 ffmpeg 合成视频...")
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        "-i", audio_path,
        "-c:v", "libx264", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        "-movflags", "+faststart",
        output_path
    ]
    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=300)
        print(f"[OK] 视频已生成: {output_path}")
        return True
    except FileNotFoundError:
        print("[警告] ffmpeg 未安装，尝试使用 moviepy...")
        return False
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode("utf-8", errors="replace") if e.stderr else "未知错误"
        print(f"[错误] ffmpeg 合成失败: {stderr}")
        return False


def create_video_moviepy(image_path, audio_path, output_path):
    """使用 moviepy 合成视频（ffmpeg 的回退方案）"""
    print("[视频] 正在使用 moviepy 合成视频...")
    try:
        from moviepy.editor import ImageClip, AudioFileClip

        audio_clip = AudioFileClip(audio_path)
        image_clip = ImageClip(image_path, duration=audio_clip.duration)
        video = image_clip.set_audio(audio_clip)
        video.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            audio_bitrate="192k",
            preset="medium",
            logger=None,
        )
        print(f"[OK] 视频已生成: {output_path}")
        return True
    except ImportError:
        print("[错误] moviepy 也未安装。请安装: pip install moviepy")
        return False
    except Exception as e:
        print(f"[错误] moviepy 合成失败: {e}")
        return False


# ========== 查找最新文章 ==========

def find_latest_article():
    """在 content/posts/ 中找到最新修改的 .md 文件"""
    posts_dir = Path(CONTENT_DIR)
    if not posts_dir.exists():
        print(f"[错误] 文章目录不存在: {os.path.abspath(CONTENT_DIR)}")
        return None

    md_files = sorted(posts_dir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not md_files:
        print(f"[错误] 在 {os.path.abspath(CONTENT_DIR)} 中未找到 .md 文件")
        return None

    latest = md_files[0]
    print(f"[OK] 找到最新文章: {latest.name}")
    return str(latest)


# ========== 主流程 ==========

def process_article(article_path, dry_run=False):
    """处理单篇文章: 解析 -> 旁白 -> TTS -> 视频"""
    article_path = os.path.abspath(article_path)

    if not os.path.exists(article_path):
        print(f"[错误] 文章文件不存在: {article_path}")
        return None

    print(f"\n{'=' * 50}")
    print(f"处理文章: {os.path.basename(article_path)}")
    print(f"{'=' * 50}\n")

    # 1. 读取并解析文章
    with open(article_path, "r", encoding="utf-8") as f:
        raw = f.read()

    meta, body = parse_frontmatter(raw)
    title = meta.get("title", "Unknown Title")
    description = meta.get("description", "")
    cover = meta.get("cover", "") or meta.get("image", "") or meta.get("featured_image", "")
    tags = meta.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip().strip('"\'') for t in tags.split(",")]

    slug = os.path.splitext(os.path.basename(article_path))[0]

    print(f"标题: {title}")
    print(f"封面: {cover or '(无)'}")
    print(f"标签: {tags}")

    # 2. 提取内容并生成旁白
    sections = extract_sections(body)
    narration = generate_narration(title, description, sections)
    print(f"\n[旁白脚本] ({len(narration.split())} 词):\n{narration}\n")

    if dry_run:
        print("[DRY RUN] 仅生成旁白脚本，不创建视频。")
        return {
            "title": title,
            "slug": slug,
            "narration": narration,
            "tags": tags,
            "description": description,
        }

    # 3. 创建临时工作目录
    os.makedirs(VIDEO_OUTPUT_DIR, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = os.path.join(tmpdir, "narration.mp3")
        image_path = os.path.join(tmpdir, "cover.jpg")
        thumb_path = os.path.join(VIDEO_OUTPUT_DIR, f"{slug}_thumb.jpg")
        video_path = os.path.join(VIDEO_OUTPUT_DIR, f"{slug}.mp4")

        # 4. 生成 TTS 音频
        if not generate_tts_audio(narration, audio_path):
            print("[错误] 无法继续，TTS 音频生成失败。")
            return None

        # 5. 获取/生成封面图片
        image_ready = False
        if cover:
            # 尝试下载封面图
            if not cover.startswith("http"):
                # 相对路径，尝试拼接 Hugo static 路径
                static_cover = os.path.join(SCRIPT_DIR, "..", "static", cover.lstrip("/"))
                if os.path.exists(static_cover):
                    shutil.copy2(static_cover, image_path)
                    image_ready = True
                    print(f"[OK] 封面已复制: {static_cover}")
            else:
                image_ready = download_image(cover, image_path)

        if not image_ready:
            # 使用 AI 生成封面
            if not generate_cover_image(title, image_path):
                print("[错误] 无法获取封面图片，无法创建视频。")
                return None

        # 6. 创建缩略图
        create_thumbnail(image_path, thumb_path)

        # 7. 合成视频
        success = create_video_ffmpeg(image_path, audio_path, video_path)
        if not success:
            success = create_video_moviepy(image_path, audio_path, video_path)
        if not success:
            print("[错误] 视频合成失败。")
            return None

    # 8. 输出结果
    video_size = os.path.getsize(video_path)
    print(f"\n{'=' * 50}")
    print(f"[完成] 视频已生成!")
    print(f"  标题: {title}")
    print(f"  视频: {os.path.abspath(video_path)}")
    print(f"  缩略图: {os.path.abspath(thumb_path)}")
    print(f"  大小: {video_size / 1024 / 1024:.1f} MB")
    print(f"{'=' * 50}\n")

    return {
        "title": title,
        "slug": slug,
        "video_path": os.path.abspath(video_path),
        "thumb_path": os.path.abspath(thumb_path),
        "tags": tags,
        "description": description,
        "narration": narration,
    }


def main():
    parser = argparse.ArgumentParser(description="Hugo 文章转 YouTube 短视频")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--article", type=str, help="Hugo .md 文章路径")
    group.add_argument("--latest", action="store_true", help="自动选择最新文章")
    parser.add_argument("--dry-run", action="store_true", help="仅生成旁白脚本，不创建视频")

    args = parser.parse_args()

    if args.latest:
        article_path = find_latest_article()
        if not article_path:
            sys.exit(1)
    else:
        article_path = args.article

    result = process_article(article_path, dry_run=args.dry_run)
    if result:
        # 输出 downstream 可用的信息
        print(f"VIDEO_TITLE={result['title']}")
        print(f"VIDEO_SLUG={result['slug']}")
        if "video_path" in result:
            print(f"VIDEO_PATH={result['video_path']}")
        print(f"VIDEO_TAGS={','.join(result['tags']) if result['tags'] else ''}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()