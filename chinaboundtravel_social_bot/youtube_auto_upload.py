#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube 自动发布 - 文章转视频并上传到 YouTube
完整流水线: Hugo 文章 -> 旁白 TTS -> 视频 -> YouTube 上传
"""

import argparse
import json
import os
import sys
import time

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
TOKEN_URL = "https://oauth2.googleapis.com/token"
YOUTUBE_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos?part=snippet,status"
BLOG_BASE_URL = "https://chinaboundtravel.com"
DEFAULT_TAGS = ["#ChinaTravel", "#ChinaBoundTravel"]
YOUTUBE_CATEGORY = "22"  # Travel & Events
CHUNK_SIZE = 10 * 1024 * 1024  # 10MB per chunk for resumable upload


# ========== OAuth 凭据加载 ==========

def load_credentials():
    """从文件或环境变量加载 client_id 和 client_secret"""
    client_id = os.environ.get("YOUTUBE_CLIENT_ID", "")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET", "")

    # 尝试从 youtube_client_secrets.json 读取
    secrets_file = os.path.join(SCRIPT_DIR, "youtube_client_secrets.json")
    if os.path.exists(secrets_file):
        try:
            with open(secrets_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 支持 Google 标准格式
            for key in ("web", "installed"):
                if key in data:
                    client_id = data[key].get("client_id", client_id)
                    client_secret = data[key].get("client_secret", client_secret)
                    break
        except (json.JSONDecodeError, IOError) as e:
            print(f"[警告] 读取 secrets 文件失败: {e}")

    if not client_id or not client_secret:
        print("[错误] 缺少 OAuth 凭据。请设置环境变量 YOUTUBE_CLIENT_ID/YOUTUBE_CLIENT_SECRET")
        print("       或创建 youtube_client_secrets.json 文件。")
        return None, None

    return client_id, client_secret


def load_refresh_token():
    """从文件或环境变量读取 refresh_token"""
    token = os.environ.get("YOUTUBE_OAUTH_REFRESH_TOKEN", "")

    if not token:
        token_file = os.path.join(SCRIPT_DIR, "youtube_refresh_token.txt")
        if os.path.exists(token_file):
            with open(token_file, "r", encoding="utf-8") as f:
                token = f.read().strip()

    if not token:
        print("[错误] 缺少 refresh_token。请先运行 youtube_oauth.py 获取。")
        return None

    return token


def refresh_access_token(client_id, client_secret, refresh_token):
    """使用 refresh_token 获取新的 access_token"""
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    try:
        resp = requests.post(TOKEN_URL, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json().get("access_token")
    except requests.RequestException as e:
        print(f"[错误] 刷新 access_token 失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  HTTP {e.response.status_code}: {e.response.text[:200]}")
        return None


# ========== YouTube 上传 ==========

def upload_to_youtube(video_path, title, description, tags, access_token, thumb_path=None):
    """使用 resumable upload 上传视频到 YouTube"""
    # 截断标题到 100 字符
    title = title[:100]

    # 准备标签
    all_tags = list(tags or []) + DEFAULT_TAGS
    # 清理标签（YouTube 标签不含 #）
    clean_tags = [t.lstrip("#") for t in all_tags if t.strip()]
    # YouTube 标签最多 500 字符
    tags_str = ",".join(clean_tags)
    if len(tags_str) > 500:
        tags_str = tags_str[:497] + "..."

    # 构建视频描述
    full_description = description or ""
    full_description += f"\n\nRead the full guide at {BLOG_BASE_URL}"
    full_description += "\n\n#ChinaTravel #ChinaBoundTravel"

    # 构建请求 body
    body = {
        "snippet": {
            "title": title,
            "description": full_description.strip(),
            "tags": clean_tags,
            "categoryId": YOUTUBE_CATEGORY,
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
            "embeddable": True,
        },
    }

    # Step 1: 发起 resumable upload session
    print("[YouTube] 正在创建上传会话...")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    try:
        init_resp = requests.post(
            YOUTUBE_UPLOAD_URL,
            json=body,
            headers=headers,
            timeout=30,
        )
    except requests.RequestException as e:
        print(f"[错误] 创建上传会话失败: {e}")
        return None

    if init_resp.status_code not in (200, 201):
        print(f"[错误] 上传会话创建失败 (HTTP {init_resp.status_code}): {init_resp.text[:300]}")
        return None

    upload_url = init_resp.headers.get("Location")
    if not upload_url:
        print("[错误] 响应中没有 Location header，无法继续上传。")
        return None

    # Step 2: 上传视频文件（分块）
    print(f"[YouTube] 正在上传视频 ({os.path.getsize(video_path) / 1024 / 1024:.1f} MB)...")
    file_size = os.path.getsize(video_path)
    uploaded = 0

    with open(video_path, "rb") as f:
        while uploaded < file_size:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break

            start = uploaded
            end = uploaded + len(chunk) - 1
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Content-Type": "application/octet-stream",
            }

            try:
                resp = requests.put(upload_url, data=chunk, headers=headers, timeout=300)
            except requests.RequestException as e:
                print(f"[错误] 上传中断: {e}")
                return None

            uploaded += len(chunk)
            progress = (uploaded / file_size) * 100
            print(f"  上传进度: {progress:.0f}% ({uploaded / 1024 / 1024:.1f}/{file_size / 1024 / 1024:.1f} MB)")

    if resp.status_code not in (200, 201):
        print(f"[错误] 视频上传失败 (HTTP {resp.status_code}): {resp.text[:300]}")
        return None

    video_data = resp.json()
    video_id = video_data.get("id")

    if not video_id:
        print(f"[错误] 上传响应中没有 video id: {json.dumps(video_data, ensure_ascii=False)[:300]}")
        return None

    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"\n[OK] 视频已上传!")
    print(f"  YouTube URL: {youtube_url}")

    # Step 3: 上传自定义缩略图
    if thumb_path and os.path.exists(thumb_path):
        print("[YouTube] 正在上传缩略图...")
        thumb_resp = _set_thumbnail(video_id, thumb_path, access_token)
        if thumb_resp:
            print("[OK] 缩略图已设置。")
        else:
            print("[警告] 缩略图设置失败，将使用 YouTube 默认缩略图。")

    return youtube_url


def _set_thumbnail(video_id, thumb_path, access_token):
    """设置视频缩略图"""
    url = f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={video_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/octet-stream",
    }

    try:
        with open(thumb_path, "rb") as f:
            resp = requests.post(url, data=f, headers=headers, timeout=60)
        return resp.status_code in (200, 204)
    except requests.RequestException:
        return False


# ========== 文章解析与视频生成 (内联逻辑) ==========

import re
import shutil
import subprocess
import tempfile
import urllib.parse
from pathlib import Path

CONTENT_DIR = os.path.join(SCRIPT_DIR, "..", "content", "posts")
VIDEO_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "..", "static", "videos")
TTS_VOICE = "en-US-JennyNeural"
TARGET_WORD_COUNT = 150
POLLINATIONS_BASE = "https://image.pollinations.ai/prompt"


def parse_frontmatter(text):
    """解析 Hugo markdown 的 frontmatter"""
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

        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        elif value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        elif value.startswith("[") and value.endswith("]"):
            items = value[1:-1].split(",")
            value = [item.strip().strip('"\'') for item in items if item.strip()]

        meta[key] = value

    return meta, body


def extract_sections(body):
    """从 markdown body 提取段落"""
    body = re.sub(r"!\[.*?\]\(.*?\)", "", body)
    body = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", body)
    body = re.sub(r"\{\{.*?\}\}", "", body)
    paragraphs = re.split(r"\n\s*\n", body)

    sections = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        heading_match = re.match(r"^(#{1,6})\s+(.*)", p)
        if heading_match:
            sections.append({"type": "heading", "text": heading_match.group(2).strip()})
        else:
            clean = re.sub(r"[#*`\[\]>|_-]", "", p)
            clean = re.sub(r"\s+", " ", clean).strip()
            if len(clean) > 20:
                sections.append({"type": "paragraph", "text": clean})
    return sections


def generate_narration(title, description, sections):
    """生成约 150 词的旁白脚本"""
    body_paragraphs = [s["text"] for s in sections if s["type"] == "paragraph"]

    selected = []
    word_count = 0
    for p in body_paragraphs:
        words = p.split()
        selected.append(p)
        word_count += len(words)
        if word_count >= 200 or len(selected) >= 4:
            break

    if not selected:
        selected = [description or title]

    combined = " ".join(selected)
    words = combined.split()
    if len(words) > TARGET_WORD_COUNT + 30:
        words = words[:TARGET_WORD_COUNT + 30]
        combined = " ".join(words)

    intro = f"Discover {title}. "
    cta = "Subscribe to China Bound Travel for more amazing China travel guides. See you on the next adventure!"
    narration = f"{intro}{combined}. {cta}"
    narration = re.sub(r"\s+", " ", narration).strip()
    return narration


def download_image(url, output_path):
    """下载图片"""
    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(resp.content)
        return True
    except Exception as e:
        print(f"[警告] 图片下载失败: {e}")
        return False


def generate_cover_image(topic, output_path):
    """使用 Pollinations.ai 生成封面"""
    prompt = f"travel photography of {topic}, no people, no faces, no portraits, cinematic, high quality, 4k"
    encoded = urllib.parse.quote(prompt)
    url = f"{POLLINATIONS_BASE}/{encoded}?width=1280&height=720&nologo=true"
    print(f"[图片] 正在生成 AI 封面 (主题: {topic})...")
    return download_image(url, output_path)


def create_thumbnail(image_path, thumb_path):
    """创建缩略图"""
    if not os.path.exists(image_path):
        return False
    try:
        cmd = [
            "ffmpeg", "-y", "-i", image_path,
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:black",
            "-q:v", "2", thumb_path
        ]
        subprocess.run(cmd, capture_output=True, check=True, timeout=30)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        shutil.copy2(image_path, thumb_path)
        return True


def create_video_ffmpeg(image_path, audio_path, output_path):
    """ffmpeg 合成视频"""
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        "-i", audio_path,
        "-c:v", "libx264", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest", "-movflags", "+faststart",
        output_path
    ]
    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=300)
        return True
    except FileNotFoundError:
        return False
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode("utf-8", errors="replace") if e.stderr else ""
        print(f"[错误] ffmpeg 合成失败: {stderr}")
        return False


def create_video_moviepy(image_path, audio_path, output_path):
    """moviepy 回退方案"""
    try:
        from moviepy.editor import ImageClip, AudioFileClip
        audio_clip = AudioFileClip(audio_path)
        image_clip = ImageClip(image_path, duration=audio_clip.duration)
        video = image_clip.set_audio(audio_clip)
        video.write_videofile(output_path, fps=24, codec="libx264",
                              audio_codec="aac", audio_bitrate="192k",
                              preset="medium", logger=None)
        return True
    except ImportError:
        print("[错误] moviepy 也未安装。请安装: pip install moviepy")
        return False
    except Exception as e:
        print(f"[错误] moviepy 合成失败: {e}")
        return False


def find_latest_article():
    """找到最新文章"""
    posts_dir = Path(CONTENT_DIR)
    if not posts_dir.exists():
        print(f"[错误] 文章目录不存在: {os.path.abspath(CONTENT_DIR)}")
        return None
    md_files = sorted(posts_dir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not md_files:
        print(f"[错误] 未找到 .md 文件")
        return None
    print(f"[OK] 最新文章: {md_files[0].name}")
    return str(md_files[0])


def process_article(article_path, dry_run=False):
    """完整处理文章: 解析 -> TTS -> 视频"""
    article_path = os.path.abspath(article_path)
    if not os.path.exists(article_path):
        print(f"[错误] 文章不存在: {article_path}")
        return None

    print(f"\n{'=' * 50}")
    print(f"处理文章: {os.path.basename(article_path)}")
    print(f"{'=' * 50}\n")

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

    sections = extract_sections(body)
    narration = generate_narration(title, description, sections)
    print(f"\n[旁白脚本] ({len(narration.split())} 词):\n{narration}\n")

    if dry_run:
        print("[DRY RUN] 仅生成旁白脚本，不创建视频。")
        return {"title": title, "slug": slug, "narration": narration,
                "tags": tags, "description": description}

    os.makedirs(VIDEO_OUTPUT_DIR, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = os.path.join(tmpdir, "narration.mp3")
        image_path = os.path.join(tmpdir, "cover.jpg")
        thumb_path = os.path.join(VIDEO_OUTPUT_DIR, f"{slug}_thumb.jpg")
        video_path = os.path.join(VIDEO_OUTPUT_DIR, f"{slug}.mp4")

        # TTS
        print(f"[TTS] 正在生成语音...")
        try:
            communicate = edge_tts.Communicate(narration, TTS_VOICE)
            communicate.save(audio_path)
            print(f"[OK] 语音已生成。")
        except Exception as e:
            print(f"[错误] TTS 失败: {e}")
            return None

        # 封面图片
        image_ready = False
        if cover:
            if not cover.startswith("http"):
                static_cover = os.path.join(SCRIPT_DIR, "..", "static", cover.lstrip("/"))
                if os.path.exists(static_cover):
                    shutil.copy2(static_cover, image_path)
                    image_ready = True
            else:
                image_ready = download_image(cover, image_path)

        if not image_ready:
            if not generate_cover_image(title, image_path):
                print("[错误] 无法获取封面图片。")
                return None

        # 缩略图
        create_thumbnail(image_path, thumb_path)

        # 视频合成
        print("[视频] 正在合成视频...")
        success = create_video_ffmpeg(image_path, audio_path, video_path)
        if not success:
            success = create_video_moviepy(image_path, audio_path, video_path)
        if not success:
            print("[错误] 视频合成失败。")
            return None

    video_size = os.path.getsize(video_path)
    print(f"\n[完成] 视频已生成!")
    print(f"  标题: {title}")
    print(f"  视频: {os.path.abspath(video_path)}")
    print(f"  缩略图: {os.path.abspath(thumb_path)}")
    print(f"  大小: {video_size / 1024 / 1024:.1f} MB\n")

    return {"title": title, "slug": slug,
            "video_path": os.path.abspath(video_path),
            "thumb_path": os.path.abspath(thumb_path),
            "tags": tags, "description": description,
            "narration": narration}


# ========== 主流水线 ==========

def run_pipeline(article_path, dry_run=False):
    """完整流水线: 文章 -> 视频 -> YouTube 上传"""
    # Step 1: 生成视频
    result = process_article(article_path, dry_run=dry_run)
    if not result:
        print("[错误] 视频生成失败，流水线终止。")
        sys.exit(1)

    if dry_run:
        print("\n[DRY RUN] 跳过 YouTube 上传。")
        return

    video_path = result.get("video_path")
    thumb_path = result.get("thumb_path")

    if not video_path or not os.path.exists(video_path):
        print(f"[错误] 视频文件不存在: {video_path}")
        sys.exit(1)

    # Step 2: 加载凭据
    print("[YouTube] 正在准备上传...")
    client_id, client_secret = load_credentials()
    if not client_id or not client_secret:
        sys.exit(1)

    refresh_token = load_refresh_token()
    if not refresh_token:
        sys.exit(1)

    # Step 3: 刷新 access_token
    print("[YouTube] 正在刷新 access_token...")
    access_token = refresh_access_token(client_id, client_secret, refresh_token)
    if not access_token:
        sys.exit(1)
    print("[OK] access_token 已获取。")

    # Step 4: 上传视频
    youtube_url = upload_to_youtube(
        video_path=video_path,
        title=result["title"],
        description=result["description"],
        tags=result["tags"],
        access_token=access_token,
        thumb_path=thumb_path,
    )

    if youtube_url:
        print(f"\n{'=' * 50}")
        print(f"[全部完成] 视频已发布到 YouTube!")
        print(f"  标题: {result['title']}")
        print(f"  URL:  {youtube_url}")
        print(f"{'=' * 50}")
    else:
        print("[错误] YouTube 上传失败。")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Hugo 文章 -> YouTube 视频自动发布")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--article", type=str, help="Hugo .md 文章路径")
    group.add_argument("--latest", action="store_true", help="自动选择最新文章")
    parser.add_argument("--dry-run", action="store_true", help="仅生成旁白和视频，不上传")

    args = parser.parse_args()

    if args.latest:
        article_path = find_latest_article()
        if not article_path:
            sys.exit(1)
    else:
        article_path = args.article

    run_pipeline(article_path, dry_run=args.dry_run)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)