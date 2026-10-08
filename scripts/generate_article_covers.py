#!/usr/bin/env python3
"""为缺封面的文章生成本地封面图。

cover_gate.py 能检测缺封面并阻断提交，但仓库里没有任何东西真正生成封面 —— 这个
脚本补上这个缺口，形成闭环：

  1. 找出 front-matter 里没有封面的文章（判定规则与 cover_gate.py 一致）
  2. 用 Agnes AI 生成贴合主题的图（兜底 Ark Seedream）
  3. 存到 static/img/ 由本站本地托管 —— cover_gate 拒绝外部域名和 AI 图域，
     所以文件必须落地本地，不能留外链
  4. 回写 front-matter 的 cover 块

密钥从环境变量 / .env 读取，全程不打印。

用法:
    python scripts/generate_article_covers.py --dry-run
    python scripts/generate_article_covers.py
    python scripts/generate_article_covers.py --only itine

主题提示词刻意写成通用风景，不指向具体真实地点，避免 AI 生成的图把某个真实
地点说成别的样子。
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:  # noqa: BLE001 - dotenv 缺失时退回纯环境变量
    pass

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "content" / "posts"
IMG_ROOT = ROOT / "static" / "img" / "china-dest" / "general"
SITE = "https://www.chinaboundtravel.com"

PROMPTS = {
    "itinerar": ("Scenic Chinese landscape at golden hour with misty mountains, "
                 "a winding river and a traditional village in the valley, wide "
                 "travel photography, natural light"),
    "solo-travel": ("Bright modern hostel common room with a wooden sofa and a large "
                    "window overlooking a busy Chinese city street, a backpack on a "
                    "chair, warm evening light, travel photography"),
    "kung-fu": ("Traditional Chinese martial arts training courtyard with ancient "
                "temple architecture, red pillars and a tiled roof, wooden training "
                "poles against a whitewashed wall, soft daylight, travel photography"),
    "monthly-update": ("Wide aerial view of a Chinese scenic landscape with layered "
                       "mountains, a curving river and terraced hills at dawn, "
                       "mist, travel photography"),
}
DEFAULT_PROMPT = ("Scenic Chinese travel scene with layered mountains, traditional "
                  "architecture and natural light, wide travel photography")


def front_matter(text: str) -> tuple[str, str, bool]:
    """返回 (front-matter 正文, 剩余正文, 是否 TOML)。"""
    m = re.match(r"^---\s*\n(.*?)\n---\n?(.*)$", text, re.DOTALL)
    if m:
        return m.group(1), m.group(2), False
    m = re.match(r"^\+\+\+\s*\n(.*?)\n\+\+\+\n?(.*)$", text, re.DOTALL)
    if m:
        return m.group(1), m.group(2), True
    return "", text, False


def has_cover(fm: str, is_toml: bool) -> bool:
    """与 cover_gate.py 等价：cover 块内有 image 即算有封面。"""
    in_cover = False
    for line in fm.split("\n"):
        stripped = line.strip()
        if is_toml:
            if stripped == "[cover]":
                in_cover = True
                continue
            if in_cover:
                if stripped.startswith("image") and "=" in stripped:
                    return True
                if stripped.startswith("["):
                    in_cover = False
            continue
        if stripped.startswith("cover:"):
            inline = stripped.split(":", 1)[1].strip()
            if inline.startswith("{") and "image" in inline:
                return True
            in_cover = True
            continue
        if in_cover:
            if stripped.startswith("image:"):
                return True
            if stripped and line[:1] not in (" ", "\t"):
                in_cover = False
    return False


def pick_prompt(slug: str) -> str:
    low = slug.lower()
    for key, prompt in PROMPTS.items():
        if key in low:
            return prompt
    return DEFAULT_PROMPT


def gen_agnes(prompt: str, out_path: Path) -> bool:
    key = os.environ.get("AGNES_API_KEY", "")
    if not key:
        return False
    try:
        resp = requests.post(
            "https://apihub.agnes-ai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"},
            json={"model": "agnes-image-2.5-flash", "prompt": prompt, "size": "1280x720"},
            timeout=120,
        )
        resp.raise_for_status()
        url = (resp.json().get("data") or [{}])[0].get("url", "")
        if not url:
            return False
        img = requests.get(url, timeout=120)
        img.raise_for_status()
        out_path.write_bytes(img.content)
        return out_path.stat().st_size > 1000
    except Exception as e:  # noqa: BLE001
        print(f"      Agnes 失败: {str(e)[:120]}")
        return False


def gen_ark(prompt: str, out_path: Path) -> bool:
    key = os.environ.get("DOUBAO_ARK_API_KEY", "")
    model = os.environ.get("ARK_IMAGE_MODEL", "")
    if not key or not model:
        return False
    try:
        resp = requests.post(
            "https://ark.cn-beijing.volces.com/api/v3/images/generations",
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"},
            json={"model": model, "prompt": prompt, "size": "1280x720",
                  "response_format": "url"},
            timeout=120,
        )
        resp.raise_for_status()
        url = (resp.json().get("data") or [{}])[0].get("url", "")
        if not url:
            return False
        img = requests.get(url, timeout=120)
        img.raise_for_status()
        out_path.write_bytes(img.content)
        return out_path.stat().st_size > 1000
    except Exception as e:  # noqa: BLE001
        print(f"      Ark 失败: {str(e)[:120]}")
        return False


def gen(prompt: str, out_path: Path) -> bool:
    return gen_agnes(prompt, out_path) or gen_ark(prompt, out_path)


def sniff_ext(data: bytes) -> str:
    """按魔数判定真实格式。

    生图 API 常无视请求的 size/格式参数直接返回 PNG —— 若不检测就套 .jpg 后缀，
    会得到「扩展名与内容不符」的图，浏览器靠嗅探能显示，但 Hugo 的图片管线按
    扩展名处理会出问题。所以必须按真实字节定名。
    """
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:4] == b"\x89PNG":
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return "jpg"


def ensure_image(slug: str, prompt: str) -> Path | None:
    """返回可用本地图路径：已有则复用，否则生成并按真实格式命名。"""
    for ext in ("webp", "jpg", "png"):
        cand = IMG_ROOT / f"{slug}.{ext}"
        if cand.exists() and cand.stat().st_size > 1000:
            return cand
    tmp = IMG_ROOT / f"{slug}.gen"
    if not gen(prompt, tmp):
        tmp.unlink(missing_ok=True)
        return None
    final = tmp.with_suffix("." + sniff_ext(tmp.read_bytes()))
    if final.exists():
        tmp.unlink(missing_ok=True)
        return final
    tmp.rename(final)
    return final


def patch_cover(path: Path, public_url: str, alt: str) -> bool:
    text = path.read_text(encoding="utf-8")
    fm, body, is_toml = front_matter(text)
    if not fm:
        print(f"      跳过：无 front-matter")
        return False
    if has_cover(fm, is_toml):
        print(f"      跳过：已有封面")
        return False
    # image 放第一行 —— 同时兼容 cover_gate 修复前后的 YAML 解析器
    if is_toml:
        block = f'\n[cover]\nimage = "{public_url}"\nalt = "{alt}"\n'
        path.write_text("+++\n" + fm.rstrip("\n") + "\n" + block + "+++\n" + body,
                        encoding="utf-8")
    else:
        block = f'cover:\n  image: "{public_url}"\n  alt: "{alt}"\n'
        path.write_text("---\n" + fm.rstrip("\n") + "\n" + block + "---\n" + body,
                        encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="为缺封面的文章生成本地封面图")
    ap.add_argument("--dry-run", action="store_true", help="只列出，不生成不改动")
    ap.add_argument("--only", default="", help="只处理 slug 含此片段的文章")
    args = ap.parse_args()

    print("密钥状态: AGNES=%s DOUBAO_ARK=%s ARK_IMAGE_MODEL=%s"
          % (bool(os.environ.get("AGNES_API_KEY")),
             bool(os.environ.get("DOUBAO_ARK_API_KEY")),
             bool(os.environ.get("ARK_IMAGE_MODEL"))))

    todo = []
    for path in sorted(POSTS.glob("*.md")):
        fm, _, is_toml = front_matter(path.read_text(encoding="utf-8", errors="replace"))
        if has_cover(fm, is_toml):
            continue
        # [=:] 同时兼容 YAML (key: v) 与 TOML (key = v)
        slug_m = re.search(r'^slug\s*[=:]\s*["\']?([^"\'\n]+)', fm, re.M)
        title_m = re.search(r'^title\s*[=:]\s*["\']?([^"\'\n]+)', fm, re.M)
        slug = slug_m.group(1).strip() if slug_m else path.stem
        if args.only and args.only not in slug:
            continue
        todo.append((path, slug, title_m.group(1).strip() if title_m else path.stem))

    print(f"待处理 {len(todo)} 篇：")
    for path, slug, _title in todo:
        print(f"  - {path.name}  (slug: {slug})")
    if not todo:
        print("没有缺封面的文章。")
        return 0
    if args.dry_run:
        return 0

    IMG_ROOT.mkdir(parents=True, exist_ok=True)
    ok = fail = 0
    for path, slug, title in todo:
        print(f"\n处理 {path.name}")
        prompt = pick_prompt(slug)
        print(f"      prompt: {prompt[:80]}...")
        out = ensure_image(slug, prompt)
        if out is None:
            print("      生成失败（Agnes 与 Ark 都不可用），跳过")
            fail += 1
            continue
        print(f"      图片: {out.name} ({out.stat().st_size // 1024}KB)")
        public = f"{SITE}/img/china-dest/general/{out.name}"
        alt = re.sub(r'\s+', " ", title)[:110]
        if patch_cover(path, public, alt):
            print(f"      已写入封面: {public}")
            ok += 1
        else:
            fail += 1

    print(f"\n完成：成功 {ok}，失败 {fail}")
    print("运行 `python scripts/cover_gate.py` 复核。")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
