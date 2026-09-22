#!/usr/bin/env python3
"""
Site Health Agent - ChinaBound Travel 2.1
横向网站健康巡检 + 低风险自动修复 (L2权限)

巡检范围：
- Sitemap健康：301页、noindex页、404页、重复URL
- Meta/Robots：noindex/nofollow/canonical配置
- 配置一致性：工作流env与Secrets匹配
- 文件健康：JSON/MD编码、乱码、占位符
- 内容完整性：空链接、图片缺alt、Review needed
- 死链检测：内链404

自动修复（L2）：
- 添加/移除noindex、robotsdisallow
- sitemap排除（_build: list:false）
- 格式规范化、编码修复
- 占位符标记清理
"""

import os
import re
import json
import glob
import ssl
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from content_seo_policy import (
    TITLE_HARD_MAX,
    TITLE_MIN,
    TITLE_SUFFIX,
    is_title_too_long,
    truncate_title,
)

# 项目根目录
ROOT = Path(__file__).parent.parent
CONTENT_DIR = ROOT / "content"
CONFIG_DIR = ROOT / "config"
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
REPORTS_DIR = ROOT / "reports" / "site_health"
ISSUES_DIR = ROOT / "reports" / "daily_issues"

# 乱码检测模式（双编码UTF-8字符）
MOJIBAKE_PATTERN = re.compile(r'[ÃÂâäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]')
# 占位符模式
# 注意：
#   1) 不能用 re.IGNORECASE 去匹配裸词 'placeholder'——HTML 表单属性
#      placeholder="John Smith" 会被命中（content/contact.md 历史误报）。
#      英文占位符词保持全大写，不带 IGNORECASE。
#   2) 不要把 {{ ... }} 当占位符——本仓大量使用 Hugo shortcode
#      {{< affiliate-flight >}} / {{< lead-magnet-cta ... >}} / {{< soft-recommend ... >}}，
#      那是合法的联盟位与组件标记，不是残留占位符（60+ 篇正常文章都含此语法）。
#   3) 不要用 <[A-Z_]+> 匹配——HTML 标签在扫描前已剥离，该模式永远不可达。
PLACEHOLDER_PATTERNS = [
    re.compile(r'Review needed', re.IGNORECASE),
    re.compile(r'\bTODO\b'),
    re.compile(r'\bFIXME\b'),
    re.compile(r'#(?:TP|VPN)_[A-Z_]+#'),          # 项目专用追踪占位符
    re.compile(r'\bPLACEHOLDER\b'),               # 全大写独立词（无 IGNORECASE）
    re.compile(r'\[Image\s*[:\]]'),               # 未替换的图片占位提示 [Image: ...]
    re.compile(r'待完善|待补充|待填写|待填充'),
    re.compile(r'Lorem ipsum', re.IGNORECASE),
    # Template placeholders like P1, P2, P3 in headings or inline text
    re.compile(r'\bP[1-4]\s*[:：]\s*[A-Z]'),
    re.compile(r'\bChP[1-4]\b'),
]

# HTML 标签剥离：占位符检测只在标签文本上做，
# 避免 <input placeholder="..."> 这类表单属性被当成内容缺陷。
# 但 Hugo shortcode {{< ... >}} 里的 < ... > 是模板语法不是 HTML，
# 必须先保护出来再剥离，否则 shortcode 被破坏成 "{{ }}" 假占位符。
_HTML_TAG_RE = re.compile(r'<[^>]+>')
_HUGO_SHORTCODE_RE = re.compile(r'\{\{[^}]*\}\}')


def strip_html_for_scan(body):
    """剥离 HTML 标签但保留 Hugo shortcode，供占位符/乱码检测使用。"""
    if not body:
        return body
    # 先把 shortcode 换成占位符，避免内部 < ... > 被当成 HTML 标签剥掉
    shortcodes = []

    def _stash(m):
        shortcodes.append(m.group(0))
        return "\x00SC%d\x00" % (len(shortcodes) - 1)

    text = _HUGO_SHORTCODE_RE.sub(_stash, body)
    text = _HTML_TAG_RE.sub(" ", text)
    for i, sc in enumerate(shortcodes):
        text = text.replace("\x00SC%d\x00" % i, sc)
    return text

# 「Title 过短」检查豁免的交易类状态页（相对 CONTENT_DIR 的路径）。
# 这些页面的标题是功能性文案而非 SEO 标题，过短是设计使然。
# 2026-09-22 审计新增：content/success.md 的 "Payment Successful!" 19 字符
# 被 TITLE_MIN=20 判为缺陷，属阈值不适用而非内容缺陷。
SHORT_TITLE_EXEMPT = {
    "success.md",
    "cancel.md",
}

# Garbled text patterns (separate severity)
GARBLED_PATTERNS = [
    # Mid-word broken inline link: letter + [text](url) + letter (e.g. "dan[hotpot](url)pair")
    re.compile(r'[a-z]\[[^\]]{5,}\]\([^)]+\)[a-z]'),
    # Duplicate consecutive words (excluding proper nouns like "Dan Dan")
    re.compile(r'\b(of|the|and|to|in|a|is|that|for|with|on)\s+\1\b', re.IGNORECASE),
]


# --- Front matter 解析 -------------------------------------------------------
# 两个历史缺陷的集中修复：
#   1) BOM：re.match(r'^---...') 不容忍 UTF-8 BOM(\ufeff)。只要文件头有一个
#      BOM，front matter 解析就整体失效并退化为「整文件当正文扫描」，
#      于是 YAML 键名 placeholder: 被当成占位符（content/search.md 误报）。
#   2) 撇号：r'title\s*:\s*["\']?([^\"\'\n]+)' 的捕获组遇到引号内的撇号就截断，
#      "Xi'an Terracotta Army..." 被读成 "Xi"（2 字符），进而误报 title_too_short。
# 因此所有 front matter 读取都应走下面两个函数，不再各自写正则。

def split_front_matter(content):
    """拆分 Hugo front matter。返回 (front_matter, body)；无 front matter 返回 (None, body)。"""
    text = content.lstrip('\ufeff') if content else content
    m = re.match(r'^---\s*\n(.*?)\n---[ \t]*\r?\n?', text, re.DOTALL)
    if not m:
        return None, text
    return m.group(1), text[m.end():]


def front_matter_field(front_matter, name):
    """取 front matter 中的标量字段值。正确处理带引号值内的撇号。

    front_matter 为 None 时返回 None。无引号值会剥离行尾注释。
    """
    if not front_matter:
        return None
    m = re.search(r'^[ \t]*%s[ \t]*:[ \t]*(.*)$' % re.escape(name),
                  front_matter, re.MULTILINE)
    if not m:
        return None
    raw = m.group(1).strip()
    if raw and raw[0] in ('"', "'"):
        quote = raw[0]
        end = raw.find(quote, 1)
        if end > 0:
            return raw[1:end].strip() or None
    # 无引号：剥离行尾注释（'# ...'），YAML 里井号前必须有空白才算注释
    raw = re.sub(r'\s+#.*$', '', raw).strip()
    return raw or None
# --- End front matter 解析 ---------------------------------------------------


def ensure_dirs():
    """确保输出目录存在"""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ISSUES_DIR.mkdir(parents=True, exist_ok=True)


def load_resolved_issues():
    """加载历史报告中已解决的问题（用于继承状态，避免重复报告）"""
    resolved = {}
    RESOLVED_STATUSES = {"resolved", "fixed", "false_positive", "closed"}
    try:
        reports = sorted(REPORTS_DIR.glob("site_health_*.json"))
        if not reports:
            return resolved
        # 读取最近3份报告，合并已解决问题
        for report_file in reports[-3:]:
            try:
                report = json.loads(report_file.read_text(encoding="utf-8"))
                for issue in report.get("issues", []):
                    status = (issue.get("status") or "").lower()
                    if status in RESOLVED_STATUSES:
                        # 用 type+page+message 作为唯一键
                        key = f"{issue.get('type','')}|{issue.get('page','')}|{issue.get('message','')[:50]}"
                        resolved[key] = {
                            "status": status,
                            "resolved_by": issue.get("resolved_by", "historical"),
                            "resolution_note": issue.get("resolution_note", "历史已解决"),
                            "resolved_at": issue.get("resolved_at", report.get("timestamp", "")),
                        }
            except Exception:
                continue
    except Exception:
        pass
    return resolved


def check_sitemap_health():
    """检查sitemap健康：noindex页、重复canonical页"""
    issues = []
    sitemap_path = ROOT / "public" / "sitemap.xml"
    
    if not sitemap_path.exists():
        return issues
    
    sitemap_content = sitemap_path.read_text(encoding="utf-8", errors="replace")
    sitemap_urls = re.findall(r'<loc>(.*?)</loc>', sitemap_content)
    
    # 检查content中的noindex页面是否在sitemap中
    for md_file in CONTENT_DIR.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
            front_matter_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
            if not front_matter_match:
                continue
            
            front_matter = front_matter_match.group(1)
            
            # 检查是否有noindex
            has_noindex = bool(re.search(r'robots\s*:\s*noindex|robotsdisallow\s*:\s*true', front_matter))
            has_build_list_false = bool(re.search(r'_build\s*:.*?list\s*:\s*false', front_matter, re.DOTALL))
            
            if has_noindex and not has_build_list_false:
                # 推断URL
                slug_match = re.search(r'slug\s*:\s*["\']?([^"\'\n]+)', front_matter)
                url_path = slug_match.group(1) if slug_match else md_file.stem
                
                # 检查是否在sitemap中
                if any(url_path in url for url in sitemap_urls):
                    issues.append({
                        "type": "sitemap_noindex_page",
                        "severity": "high",
                        "file": str(md_file.relative_to(ROOT)),
                        "message": f"noindex页面仍在sitemap中: {url_path}",
                        "auto_fixable": True,
                        "fix_action": "add_build_list_false",
                        "agent": "site_health"
                    })
        except Exception as e:
            issues.append({
                "type": "file_read_error",
                "severity": "low",
                "file": str(md_file.relative_to(ROOT)),
                "message": f"读取失败: {str(e)}",
                "auto_fixable": False,
                "agent": "site_health"
            })
    
    return issues


def check_meta_robots():
    """检查Meta/Robots配置：search页面是否noindex"""
    issues = []
    
    search_file = CONTENT_DIR / "search.md"
    if search_file.exists():
        content = search_file.read_text(encoding="utf-8", errors="replace")
        if not re.search(r'robotsdisallow\s*:\s*true|robots\s*:\s*noindex', content):
            issues.append({
                "type": "search_page_noindex_missing",
                "severity": "high",
                "file": "content/search.md",
                "message": "/search/ 页面未设置noindex",
                "auto_fixable": True,
                "fix_action": "add_robotsdisallow",
                "agent": "site_health"
            })
    
    return issues


def check_file_encoding():
    """检查文件编码和乱码"""
    issues = []
    
    # 检查JSON文件
    for json_file in list(CONFIG_DIR.glob("*.json")) + list((REPORTS_DIR.parent / "growth_memory").glob("*.json")) + list((REPORTS_DIR.parent / "measurement").glob("*.json")):
        try:
            raw_bytes = json_file.read_bytes()
            # 检测BOM
            has_bom = raw_bytes.startswith(b'\xef\xbb\xbf')
            content = raw_bytes.decode('utf-8-sig' if has_bom else 'utf-8')
            
            if has_bom:
                issues.append({
                    "type": "file_bom",
                    "severity": "medium",
                    "file": str(json_file.relative_to(ROOT)),
                    "message": "文件包含UTF-8 BOM",
                    "auto_fixable": True,
                    "fix_action": "remove_bom",
                    "agent": "site_health"
                })
            
            if MOJIBAKE_PATTERN.search(content):
                issues.append({
                    "type": "file_mojibake",
                    "severity": "medium",
                    "file": str(json_file.relative_to(ROOT)),
                    "message": f"检测到乱码字符（双编码）",
                    "auto_fixable": True,
                    "fix_action": "fix_encoding",
                    "agent": "site_health"
                })
            # 验证JSON有效性
            json.loads(content)
        except UnicodeDecodeError:
            issues.append({
                "type": "file_encoding_error",
                "severity": "high",
                "file": str(json_file.relative_to(ROOT)),
                "message": "UTF-8解码失败",
                "auto_fixable": True,
                "fix_action": "fix_encoding",
                "agent": "site_health"
            })
        except json.JSONDecodeError as e:
            issues.append({
                "type": "json_invalid",
                "severity": "high",
                "file": str(json_file.relative_to(ROOT)),
                "message": f"JSON格式错误: {str(e)[:100]}",
                "auto_fixable": False,
                "agent": "site_health"
            })
    
    return issues


def check_content_placeholders():
    """检查内容中的占位符和状态标记暴露"""
    issues = []
    
    # 排除目录
    # 与 check_title_meta_length() 保持一致：_draft（注意不是 _drafts）与
    # .archived 也要排除。草稿是进行中的稿件，扫描它们只产出噪音。
    EXCLUDE_DIRS = ['drafts', '_drafts', '_draft', '.audit_backup', '.archived']
    
    for md_file in CONTENT_DIR.rglob("*.md"):
        # 跳过排除目录
        rel_path = str(md_file.relative_to(ROOT))
        if any(exclude in rel_path for exclude in EXCLUDE_DIRS):
            continue
            
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
            # 只检查正文（front matter 之后）
            # 走 split_front_matter()：BOM 容错，且保证 YAML 键名不被当成正文扫描
            _fm, body = split_front_matter(content)
            # 剥离 HTML 标签（保留 Hugo shortcode），占位符检测只在标签文本上做
            # （否则 <input placeholder="..."> 表单属性会被当成内容缺陷）
            scan_text = strip_html_for_scan(body)

            for pattern in PLACEHOLDER_PATTERNS:
                matches = pattern.findall(scan_text)
                if matches:
                    issues.append({
                        "type": "content_placeholder",
                        "severity": "high",
                        "file": rel_path,
                        "message": f"发现模板占位符: {matches[0]}",
                        "auto_fixable": False,
                        "agent": "content"
                    })
                    break

            # Check for garbled text patterns
            for gpattern in GARBLED_PATTERNS:
                gmatches = gpattern.findall(body)
                if gmatches:
                    # Get context
                    gmatches2 = list(gpattern.finditer(body))
                    ctx = body[max(0, gmatches2[0].start()-20):gmatches2[0].end()+20].replace('\n', ' ')
                    issues.append({
                        "type": "garbled_text",
                        "severity": "high",
                        "file": rel_path,
                        "message": f"疑似乱码/文本损坏: ...{ctx}...",
                        "auto_fixable": False,
                        "agent": "content"
                    })
                    break
        except Exception:
            pass
    
    return issues


def check_workflow_env_consistency():
    """检查工作流env配置一致性"""
    issues = []
    
    # 检查social-engine-daily中的Buffer变量名
    social_workflow = WORKFLOWS_DIR / "social-engine-daily.yml"
    if social_workflow.exists():
        content = social_workflow.read_text(encoding="utf-8", errors="replace")
        if 'BUFFER_ACCESS_TOKEN' in content and 'BUFFER_API_TOKEN_A' not in content:
            issues.append({
                "type": "workflow_env_mismatch",
                "severity": "high",
                "file": ".github/workflows/social-engine-daily.yml",
                "message": "使用BUFFER_ACCESS_TOKEN但Secrets中是BUFFER_API_TOKEN_A",
                "auto_fixable": True,
                "fix_action": "fix_env_var_name",
                "agent": "site_health"
            })
    
    return issues


def check_empty_links():
    """检查空链接：href="#"、href=""、javascript:void(0)"""
    issues = []
    EMPTY_LINK_PATTERNS = [
        re.compile(r"href\s*=\s*[\"']#[\"']"),
        re.compile(r"href\s*=\s*[\"']{2}"),
        re.compile(r"href\s*=\s*[\"']javascript:void\(0\)[\"']", re.IGNORECASE),
    ]
    
    for md_file in CONTENT_DIR.rglob("*.md"):
        rel_path = str(md_file.relative_to(ROOT))
        if any(exclude in rel_path for exclude in ['drafts', '.audit_backup', '_drafts', '_draft', '.archived']):
            continue
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
            front_matter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
            body = content[front_matter_match.end():] if front_matter_match else content
            
            for pattern in EMPTY_LINK_PATTERNS:
                if pattern.search(body):
                    issues.append({
                        "type": "empty_link",
                        "severity": "medium",
                        "file": rel_path,
                        "message": "发现空链接（href=#或空href）",
                        "auto_fixable": False,
                        "agent": "content"
                    })
                    break
        except Exception:
            pass
    return issues


def check_image_alt():
    """检查图片缺alt属性"""
    issues = []
    IMG_NO_ALT = re.compile(r'!\[[^\]]*\]\([^)]+\)|<img(?![^>]*alt=)[^>]*>', re.IGNORECASE)
    
    for md_file in CONTENT_DIR.rglob("*.md"):
        rel_path = str(md_file.relative_to(ROOT))
        if any(exclude in rel_path for exclude in ['drafts', '.audit_backup', '_drafts', '_draft', '.archived']):
            continue
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
            front_matter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
            body = content[front_matter_match.end():] if front_matter_match else content
            
            # 检查Markdown图片 ![]() - alt为空
            md_images = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', body)
            for alt_text, img_url in md_images:
                if not alt_text.strip():
                    issues.append({
                        "type": "image_missing_alt",
                        "severity": "medium",
                        "file": rel_path,
                        "message": f"图片缺alt: {img_url[:50]}",
                        "auto_fixable": False,
                        "agent": "content"
                    })
            
            # 检查HTML img标签无alt
            html_imgs = re.findall(r'<img(?![^>]*alt=)[^>]*>', body, re.IGNORECASE)
            for img in html_imgs:
                issues.append({
                    "type": "image_missing_alt",
                    "severity": "medium",
                    "file": rel_path,
                    "message": "HTML img标签缺alt属性",
                    "auto_fixable": False,
                    "agent": "content"
                })
        except Exception:
            pass
    return issues


def check_draft_leak():
    """检查草稿泄露：draft:true但内容已发布"""
    issues = []
    
    for md_file in CONTENT_DIR.rglob("*.md"):
        rel_path = str(md_file.relative_to(ROOT))
        if any(exclude in rel_path for exclude in ['drafts', '.audit_backup', '_drafts', '_draft', '.archived']):
            continue
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
            front_matter_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
            if not front_matter_match:
                continue
            front_matter = front_matter_match.group(1)
            
            if re.search(r'draft\s*:\s*true', front_matter, re.IGNORECASE):
                issues.append({
                    "type": "draft_leak",
                    "severity": "high",
                    "file": rel_path,
                    "message": "draft:true的文章可能已发布到线上",
                    "auto_fixable": False,
                    "agent": "content"
                })
        except Exception:
            pass
    return issues


def check_persona_violation():
    """检查Persona违规：禁止使用第一人称经历表述"""
    issues = []
    PERSONA_FORBIDDEN = [
        re.compile(r'I lived in China for', re.IGNORECASE),
        re.compile(r'My wife', re.IGNORECASE),
        re.compile(r'I personally tested', re.IGNORECASE),
        re.compile(r'I stayed at', re.IGNORECASE),
        re.compile(r'As a local', re.IGNORECASE),
        re.compile(r'My favorite', re.IGNORECASE),
        re.compile(r'China insider', re.IGNORECASE),
        re.compile(r'I tried', re.IGNORECASE),
    ]
    
    for md_file in CONTENT_DIR.rglob("*.md"):
        rel_path = str(md_file.relative_to(ROOT))
        if any(exclude in rel_path for exclude in ['drafts', '.audit_backup', '_drafts', '_draft', '.archived']):
            continue
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
            front_matter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
            body = content[front_matter_match.end():] if front_matter_match else content
            
            for pattern in PERSONA_FORBIDDEN:
                matches = pattern.findall(body)
                if matches:
                    issues.append({
                        "type": "persona_violation",
                        "severity": "high",
                        "file": rel_path,
                        "message": f"Persona违规: {pattern.pattern[:40]}",
                        "auto_fixable": False,
                        "agent": "content"
                    })
                    break
        except Exception:
            pass
    return issues


def check_ai_forbidden_words():
    """检查AI禁用词：Best/Cheapest/Guaranteed/#1/Secret"""
    issues = []
    AI_FORBIDDEN = [
        (re.compile(r'\bbest in China\b', re.IGNORECASE), "best in China"),
        (re.compile(r'\bcheapest\b', re.IGNORECASE), "cheapest"),
        (re.compile(r'\bguaranteed\b', re.IGNORECASE), "guaranteed"),
        (re.compile(r'#1\b', re.IGNORECASE), "#1"),
        (re.compile(r'\bsecret place\b', re.IGNORECASE), "secret place"),
        (re.compile(r'\bperfect\b', re.IGNORECASE), "perfect"),
    ]
    
    for md_file in CONTENT_DIR.rglob("*.md"):
        rel_path = str(md_file.relative_to(ROOT))
        if any(exclude in rel_path for exclude in ['drafts', '.audit_backup', '_drafts', '_draft', '.archived']):
            continue
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
            front_matter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
            body = content[front_matter_match.end():] if front_matter_match else content
            
            for pattern, word in AI_FORBIDDEN:
                if pattern.search(body):
                    issues.append({
                        "type": "ai_forbidden_word",
                        "severity": "medium",
                        "file": rel_path,
                        "message": f"AI禁用词: {word}",
                        "auto_fixable": False,
                        "agent": "content"
                    })
        except Exception:
            pass
    return issues


def check_title_meta_length():
    """检查Title和Meta description长度"""
    issues = []

    for md_file in CONTENT_DIR.rglob("*.md"):
        rel_path = str(md_file.relative_to(ROOT))
        if any(exclude in rel_path for exclude in ['drafts', '.audit_backup', '_drafts', '_draft', '.archived']):
            continue
        # 交易类状态页豁免「Title 过短」检查。
        # TITLE_MIN=20 是为 SEO 文章标题设计的下限（配合 head 模板的
        # " | ChinaBound Travel" 后缀）。支付成功/取消这类事务页的标题
        # 本来就该短，"Payment Successful!" 不是缺陷。
        # 只豁免 too_short，不豁免 too_long——事务页标题过长同样是真问题。
        # 按文件白名单，不放开整个 content/ 根目录，避免掩盖其他页面的真实短标题。
        is_short_exempt = str(md_file.relative_to(CONTENT_DIR)) in SHORT_TITLE_EXEMPT
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
            front_matter, _body = split_front_matter(content)
            if not front_matter:
                continue

            # Title长度检查
            title = front_matter_field(front_matter, "title")
            if title:
                if is_title_too_long(title):
                    issues.append({
                        "type": "title_too_long",
                        "severity": "low",
                        "file": rel_path,
                        "message": f"Title过长({len(title)}字符，模板上限{TITLE_HARD_MAX}): {title[:40]}...",
                        "auto_fixable": True,
                        "fix_action": "shorten_title",
                        "fix_hint": (
                            f"缩短 front matter title 至 {TITLE_HARD_MAX} 字符以内；"
                            f"若需保留“{TITLE_SUFFIX.strip()}”后缀，建议控制在前 "
                            f"{TITLE_HARD_MAX - len(TITLE_SUFFIX)} 字符内"
                        ),
                        "agent": "seo"
                    })
                elif len(title) < TITLE_MIN and not is_short_exempt:
                    issues.append({
                        "type": "title_too_short",
                        "severity": "low",
                        "file": rel_path,
                        "message": f"Title过短({len(title)}字符<{TITLE_MIN})",
                        "auto_fixable": False,
                        "agent": "seo"
                    })
            
            # Meta description长度检查
            desc = front_matter_field(front_matter, "description")
            if desc:
                if len(desc) > 165:
                    issues.append({
                        "type": "meta_description_too_long",
                        "severity": "low",
                        "file": rel_path,
                        "message": f"Meta description过长({len(desc)}字符)",
                        "auto_fixable": False,
                        "agent": "seo"
                    })
                elif len(desc) < 70:
                    issues.append({
                        "type": "meta_description_too_short",
                        "severity": "low",
                        "file": rel_path,
                        "message": f"Meta description过短({len(desc)}字符)",
                        "auto_fixable": False,
                        "agent": "seo"
                    })
        except Exception:
            pass
    return issues


# 网络请求配置
NETWORK_TIMEOUT = 10  # 秒
SITE_BASE_URL = "https://www.chinaboundtravel.com"
CHECK_PAGES = ["/", "/pricing/", "/contact/", "/posts/ultimate-guide-to-china-visa-for-tourists/"]


def _fetch_url(url):
    """获取URL响应，返回(response, html_content)或(None, None)
    对 HTTPError（如 Cloudflare 403）也返回响应对象，供调用方判断状态码"""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=NETWORK_TIMEOUT, context=ctx) as resp:
            html = resp.read().decode("utf-8", errors="replace")
            return resp, html
    except urllib.error.HTTPError as e:
        # Cloudflare 403/挑战页：返回响应对象供调用方判断，不视为网络失败
        try:
            html = e.read().decode("utf-8", errors="replace")
        except Exception:
            html = ""
        return e, html
    except Exception as e:
        return None, None


def record_check_failure(all_issues, check_id, check_name_cn, exc):
    """把「检查本身抛异常」记成一条 issue。

    2026-09-18 修：五个网络检查（安全头/混合内容/OG标签/SSL/结构化数据）
    此前都是 `except: print(...)` 后什么都不往 all_issues 里写。
    结果「检查失败」和「检查通过、0 个问题」在报告里长得一模一样。

    直接后果是 agent_kpi_auditor 的静默假绿灯：它读这份报告给
    ops.security_headers 打分，拿到 0 条安全发现就判 100% 合规。
    线上真的丢掉 HSTS 时报告里会出现 security_header_missing；
    但检查抛异常时一条都没有，于是照样报 100 分。
    """
    all_issues.append({
        "type": "check_failed",
        "severity": "high",
        "check": check_id,
        "file": SITE_BASE_URL,
        "message": f"{check_name_cn}失败: {exc}",
        "auto_fixable": False,
        "agent": "site_health",
    })


def check_security_headers():
    """检查安全头完整性"""
    issues = []
    REQUIRED_HEADERS = {
        "Strict-Transport-Security": "HSTS",
        "X-Content-Type-Options": "MIME类型嗅探防护",
        "X-Frame-Options": "点击劫持防护",
        "Content-Security-Policy": "CSP策略",
        "Referrer-Policy": "引荐信息控制",
        "Permissions-Policy": "权限策略",
    }
    
    resp, _ = _fetch_url(SITE_BASE_URL + "/")
    if resp is None:
        issues.append({
            "type": "site_unreachable",
            "severity": "critical",
            "file": SITE_BASE_URL,
            "message": "网站无法访问",
            "auto_fixable": False,
            "agent": "site_health"
        })
        return issues
    
    headers = {k.lower(): v for k, v in resp.headers.items()}
    for header, desc in REQUIRED_HEADERS.items():
        if header.lower() not in headers:
            issues.append({
                "type": "security_header_missing",
                "severity": "medium",
                "file": SITE_BASE_URL,
                "message": f"缺少安全头: {header} ({desc})",
                "auto_fixable": False,
                "agent": "site_health"
            })
    
    return issues


REQUIRED_CSP_HOSTS = {
    "sentry.io": "Sentry 错误追踪",
    "sentry.avs.io": "Sentry 错误追踪（自定义域名）",
    "googlesyndication.com": "Google AdSense",
    "google-analytics.com": "Google Analytics",
    "googletagmanager.com": "Google Tag Manager",
    "cloudflareinsights.com": "Cloudflare Analytics",
}
"""CSP 必须放行的关键第三方服务。

2026-09-18 补：报告 schema 从 findings[].module 迁到 issues[].type 时
丢了这批检查。旧 site_health_audit_engine.py 会检查 CSP 里是否放行
上面的域，新 check_security_headers() 只看头是否存在——6 条 HIGH/MEDIUM
发现整体消失。而 site_health_audit_engine.py 没有任何 workflow 在跑
（死代码），所以这些发现永远不会再出现。

只看「CSP 头存在」不够：放行全部的 CSP 和放行空白的 CSP
都会让 check_security_headers 通过。
"""


def check_csp_allowlist():
    """检查 CSP 是否放行了关键第三方服务。

    产出 type=csp_allowlist_missing。与 security_header_missing 区分开：
    后者是「头不存在」（ops.security_headers 考核项），
    前者是「头存在但内容不够」（不影响该 KPI，但同样是 HIGH 级发现）。

    返回 [] 的两种情况都是刻意的，避免重复上报：
      - 站点不可达 → check_security_headers 已报 site_unreachable
      - CSP 头缺失 → check_security_headers 已报 security_header_missing
    """
    issues = []
    resp, _ = _fetch_url(SITE_BASE_URL + "/")
    if resp is None:
        return issues
    headers = {k.lower(): v for k, v in resp.headers.items()}
    csp = headers.get("content-security-policy", "")
    if not csp:
        return issues

    for domain, desc in REQUIRED_CSP_HOSTS.items():
        if domain not in csp:
            issues.append({
                "type": "csp_allowlist_missing",
                "severity": "high",
                "file": SITE_BASE_URL,
                "message": f"CSP 未允许 {desc}（{domain}）",
                "detail": f"Content-Security-Policy 中未包含 {domain}，"
                          f"可能导致 {desc} 被拦截",
                "recommendation": f"在 CSP 的 script-src 和/或 connect-src 中添加 {domain}",
                # 不自动修复：CSP 改错会打断分析/广告/错误追踪，
                # 或反过来放开不必要的源。必须由人评审后改 Cloudflare 配置。
                "auto_fixable": False,
                "agent": "site_health",
            })
    return issues


def check_mixed_content():
    """检查混合内容：HTTPS页面中加载HTTP资源"""
    issues = []
    HTTP_RESOURCE_PATTERNS = [
        re.compile(r'src="http://[^"]+"', re.IGNORECASE),
        re.compile(r'href="http://[^"]+"', re.IGNORECASE),
        re.compile(r'url\(http://[^)]+\)', re.IGNORECASE),
    ]
    
    for page_path in CHECK_PAGES[:2]:  # 只检查首页和定价页
        resp, html = _fetch_url(SITE_BASE_URL + page_path)
        if html is None:
            continue
        
        for pattern in HTTP_RESOURCE_PATTERNS:
            matches = pattern.findall(html)
            if matches:
                # 排除允许的HTTP链接（如外部引用）
                for match in matches[:3]:  # 只报告前3个
                    issues.append({
                        "type": "mixed_content",
                        "severity": "medium",
                        "file": page_path,
                        "message": f"混合内容: {match[:60]}",
                        "auto_fixable": False,
                        "agent": "site_health"
                    })
                break
    
    return issues


def check_og_tags():
    """检查OG/Twitter标签完整性"""
    issues = []
    REQUIRED_OG = ["og:title", "og:description", "og:image", "og:url", "og:type"]
    REQUIRED_TWITTER = ["twitter:card", "twitter:title", "twitter:description", "twitter:image"]
    
    for page_path in CHECK_PAGES[:3]:
        resp, html = _fetch_url(SITE_BASE_URL + page_path)
        if html is None:
            continue
        # Cloudflare 拦截（403/挑战页）：HTML 非真实页面，跳过检测避免误报
        if resp is not None and getattr(resp, "status", 200) != 200:
            continue
        if len(html) < 500 or "<html" not in html.lower():
            continue

        # 检查OG标签
        for og_tag in REQUIRED_OG:
            pattern = re.compile(r"property=[\"']" + re.escape(og_tag) + r"[\"']", re.IGNORECASE)
            if not pattern.search(html):
                issues.append({
                    "type": "og_tag_missing",
                    "severity": "low",
                    "file": page_path,
                    "message": f"缺少OG标签: {og_tag}",
                    "auto_fixable": False,
                    "agent": "seo"
                })
        
        # 检查Twitter标签（宽松匹配：支持 name=twitter:card 无引号格式）
        for tw_tag in REQUIRED_TWITTER:
            pattern = re.compile(r"name=[\"']?" + re.escape(tw_tag) + r"[\"']?[\s>]", re.IGNORECASE)
            if not pattern.search(html):
                issues.append({
                    "type": "twitter_tag_missing",
                    "severity": "low",
                    "file": page_path,
                    "message": f"缺少Twitter标签: {tw_tag}",
                    "auto_fixable": False,
                    "agent": "seo"
                })
    
    return issues


def check_ssl_certificate():
    """检查SSL证书有效期"""
    issues = []
    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(SITE_BASE_URL, timeout=NETWORK_TIMEOUT, context=ctx) as resp:
            cert = resp.peer_certificate()
            if cert:
                import datetime as dt
                not_after = dt.datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
                days_left = (not_after - dt.datetime.utcnow()).days
                if days_left < 30:
                    issues.append({
                        "type": "ssl_expiring_soon",
                        "severity": "high",
                        "file": SITE_BASE_URL,
                        "message": f"SSL证书将在{days_left}天后过期",
                        "auto_fixable": False,
                        "agent": "site_health"
                    })
                elif days_left < 90:
                    issues.append({
                        "type": "ssl_expiring_warning",
                        "severity": "medium",
                        "file": SITE_BASE_URL,
                        "message": f"SSL证书将在{days_left}天后过期",
                        "auto_fixable": False,
                        "agent": "site_health"
                    })
    except urllib.error.HTTPError as e:
        # HTTP 403/401/429 = Cloudflare/访问控制拦截，SSL 握手已成功，不算 SSL 问题
        if e.code in (401, 403, 429):
            pass  # 访问控制拦截，非 SSL 问题，不报告
        else:
            issues.append({
                "type": "ssl_check_failed",
                "severity": "medium",
                "file": SITE_BASE_URL,
                "message": f"SSL检查失败(HTTP {e.code}): {str(e)[:50]}",
                "auto_fixable": False,
                "agent": "site_health"
            })
    except Exception as e:
        issues.append({
            "type": "ssl_check_failed",
            "severity": "medium",
            "file": SITE_BASE_URL,
            "message": f"SSL检查失败: {str(e)[:50]}",
            "auto_fixable": False,
            "agent": "site_health"
        })

    return issues


def check_structured_data():
    """检查结构化数据缺失"""
    issues = []
    
    for page_path in CHECK_PAGES:
        resp, html = _fetch_url(SITE_BASE_URL + page_path)
        if html is None:
            continue
        
        # 检查JSON-LD
        has_json_ld = "application/ld+json" in html
        
        # 文章页应该有Article schema
        if "/posts/" in page_path or "/cities/" in page_path:
            if not has_json_ld or "Article" not in html:
                issues.append({
                    "type": "article_schema_missing",
                    "severity": "medium",
                    "file": page_path,
                    "message": "文章页缺少Article结构化数据",
                    "auto_fixable": False,
                    "agent": "seo"
                })
        
        # 所有页面应该有Organization schema
        if not has_json_ld or "Organization" not in html:
            issues.append({
                "type": "organization_schema_missing",
                "severity": "low",
                "file": page_path,
                "message": "缺少Organization结构化数据",
                "auto_fixable": False,
                "agent": "seo"
            })
    
    return issues


def auto_fix_issue(issue):
    """自动修复问题（L2权限）"""
    if not issue.get("auto_fixable"):
        return False, "不可自动修复"
    
    fix_action = issue.get("fix_action")
    file_path = ROOT / issue["file"]
    
    try:
        if fix_action == "add_build_list_false":
            content = file_path.read_text(encoding="utf-8")
            if "draft: false" in content:
                content = content.replace("draft: false", "draft: false\n_build:\n  list: false", 1)
            elif "robots: noindex" in content:
                content = content.replace("robots: noindex", "robots: noindex\n_build:\n  list: false", 1)
            file_path.write_text(content, encoding="utf-8")
            return True, "已添加 _build: list:false"
        
        elif fix_action == "add_robotsdisallow":
            content = file_path.read_text(encoding="utf-8")
            content = content.replace(
                "date: '2026-06-02T10:00:00+08:00'",
                "date: '2026-06-02T10:00:00+08:00'\nrobotsdisallow: true",
                1
            )
            file_path.write_text(content, encoding="utf-8")
            return True, "已添加 robotsdisallow: true"
        
        elif fix_action == "remove_bom":
            raw = file_path.read_bytes()
            if raw.startswith(b'\xef\xbb\xbf'):
                file_path.write_bytes(raw[3:])
                return True, "已移除UTF-8 BOM"
            return False, "文件无BOM"
        
        elif fix_action == "fix_encoding":
            # 尝试用多种编码读取后重写为UTF-8
            for enc in ['gbk', 'gb2312', 'latin-1']:
                try:
                    content = file_path.read_text(encoding=enc)
                    file_path.write_text(content, encoding="utf-8")
                    return True, f"已从{enc}转换为UTF-8"
                except Exception:
                    continue
            return False, "无法识别原始编码"
        
        elif fix_action == "fix_env_var_name":
            content = file_path.read_text(encoding="utf-8")
            content = content.replace("secrets.BUFFER_ACCESS_TOKEN", "secrets.BUFFER_API_TOKEN_A")
            content = content.replace("secrets.BUFFER_ACCESS_TOKEN_2", "secrets.BUFFER_API_TOKEN_B")
            file_path.write_text(content, encoding="utf-8")
            return True, "已修复env变量名"
        
        elif fix_action == "shorten_title":
            # Match the actual Hugo template hard limit.
            file_content = file_path.read_text(encoding="utf-8")
            fm_match = re.match(r'^(---\s*\n)(.*?)(\n---)', file_content, re.DOTALL)
            if not fm_match:
                return False, "无 front matter"
            fm = fm_match.group(2)
            title_match = re.search(r'^(title\s*:\s*)(["\']?)([^"\'\n]+)(["\']?)$', fm, re.MULTILINE)
            if not title_match:
                return False, "无 title 字段"
            old_title = title_match.group(3).strip()
            if not is_title_too_long(old_title):
                return False, f"title 已在限长内({len(old_title)}字符)"
            new_title = truncate_title(old_title)
            # 替换 title 行
            new_fm = fm[:title_match.start(3)] + new_title + fm[title_match.end(3):]
            new_content = file_content[:fm_match.start(2)] + new_fm + file_content[fm_match.end(2):]
            file_path.write_text(new_content, encoding="utf-8")
            return True, f"title 已缩短: {len(old_title)}->{len(new_title)}字符"
        
        else:
            return False, f"未知修复操作: {fix_action}"
    
    except Exception as e:
        return False, f"修复失败: {str(e)}"


def _fetch_gtag_destinations(measurement_id):
    """拉 gtag.js?id=<id>，解析出这个 ID 实际配置了几个 GA4 目的地。

    2026-09-20 根因定位：单看页面 HTML 是**检测不出**双计的 —— 线上首页
    只有一句 gtag("config","G-GECBME3YVJ")，HTML 里只有 1 个 ID。
    真正的双计发生在 Google 服务端：

        https://www.googletagmanager.com/gtag/js?id=G-GECBME3YVJ
        -> 返回的是一个 GTM 容器载荷（"resource":{"version":"2","macros":[...]}），
           里面 __dest_ga 有**两个** vtp_destinationId：
               tag_id:1  G-GECBME3YVJ
               tag_id:7  G-P6BH500VBK
           而且每一个事件 tag 都成对复制了（__ccd_em_page_view / form / download /
           outbound_click / scroll / video / site_search / conversion_marking /
           auto_redact / gct / ga_first / ga_last 各两份）。

    即：有人在 Google Tag Manager（或 GA4 的 Google Tag）里建了一个
    Google Tag 并配了**两个目的地**。一次 gtag config 会触发整条 tag 链，
    所以每个事件都被记到两个属性上 —— users / sessions / engagement 全部双计。

    这是 Google 控制台的配置问题，不是 Cloudflare Worker / Transform Rule，
    仓库里改任何东西都修不了它。返回 (destinations, payload_len) 供上报。
    """
    url = f"https://www.googletagmanager.com/gtag/js?id={measurement_id}"
    resp, payload = _fetch_url(url)
    if resp is None or not payload:
        return [], 0
    dests = sorted(set(re.findall(
        r'"vtp_destinationId":"(G-[A-Z0-9]{8,12})"', payload)))
    if not dests:
        # 旧版载荷用 trackingId，做个兜底
        dests = sorted(set(re.findall(
            r'"vtp_trackingId":"(G-[A-Z0-9]{8,12})"', payload)))
    return dests, len(payload)


def _load_analytics_canonical_config():
    """读 config/analytics_canonical.json —— canonical 属性的显式声明。

    为什么需要一个提交进仓库的声明文件：

    GA4 的 measurement ID 和 property ID 是两套编号，仓库里历来各写各的：
    hugo.toml 写 measurement ID（G-GECBME3YVJ），各脚本查数值 property ID
    （GA4_PROPERTY_ID）。两套编号之间没有任何交叉验证 —— 直到 2026-09-20
    人工上 GA4 控制台才发现：同一个账号下有两个数据流网址完全相同的属性
    （538482322 -> G-GECBME3YVJ，541752321 -> G-P6BH500VBK），而所有脚本
    默认查的是 541752321，即一直在读那个重复属性。

    仓库侧无法证明「数值 ID 和 measurement ID 属于同一个属性」——
    GA4 Admin API 返回 401（服务账号只授权了 Data API）。所以这个映射关系
    只能靠人工在控制台核对一次，然后写进这个文件固化下来。

    文件缺失不报错：那是「还没有做过核对」，不是「坏了」。
    """
    cfg = ROOT / "config" / "analytics_canonical.json"
    try:
        return json.loads(cfg.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _read_hugo_measurement_id():
    """从 hugo.toml 读 GA4 measurement ID（PaperMod 字段 TrackingID）。"""
    cfg = ROOT / "hugo.toml"
    try:
        text = cfg.read_text(encoding="utf-8")
    except Exception:
        return ""
    m = re.search(r'TrackingID\s*=\s*"(G-[A-Z0-9]{8,12})"', text)
    if m:
        return m.group(1)
    m = re.search(r"\b(G-[A-Z0-9]{8,12})\b", text)
    return m.group(1) if m else ""


def _check_analytics_config_consistency(canonical):
    """校验 canonical 声明、hugo.toml、GA4_PROPERTY_ID 三方是否指向同一属性。

    返回 (mismatch: bool, detail: dict)。

    能查的只到「仓库内两处配置是否自相矛盾」这一步：
      - hugo.toml 的 TrackingID 不是 canonical measurement ID
      - 环境里的 GA4_PROPERTY_ID 不是 canonical property ID（或未设置）

    查不了的：property ID 与 measurement ID 的对应关系 —— 那需要 GA4 Admin
    API，而当前服务账号只有 Data API 权限。所以这个校验是「防回归」性质的：
    任何人在仓库里改了 ID 而忘了改另一处，这里会立刻报出来。
    """
    detail = {
        "canonical_property_id": canonical.get("canonical_property_id", ""),
        "canonical_measurement_id": canonical.get("canonical_measurement_id", ""),
        "hugo_measurement_id": _read_hugo_measurement_id(),
        "env_property_id": os.environ.get("GA4_PROPERTY_ID", "").strip(),
        "canonical_config_present": bool(canonical),
    }
    if not canonical:
        return False, detail
    reasons = []
    if detail["hugo_measurement_id"] and \
            detail["hugo_measurement_id"] != canonical["canonical_measurement_id"]:
        reasons.append(
            f"hugo.toml TrackingID={detail['hugo_measurement_id']} "
            f"!= canonical {canonical['canonical_measurement_id']}")
    if detail["env_property_id"] and \
            detail["env_property_id"] != canonical["canonical_property_id"]:
        reasons.append(
            f"GA4_PROPERTY_ID={detail['env_property_id']} "
            f"!= canonical {canonical['canonical_property_id']}")
    return bool(reasons), {**detail, "mismatch_reasons": reasons}


def check_analytics_measurement_ids():
    """检查 GA4 是否被双计，并写出机器可读的姿态报告。

    为什么单独做一个「姿态文件」而不只记 issue：

    双 GA4 是 **Google 服务端配置**问题，仓库和静态站闸门结构性都看不见。
    2026-09-20 实测：线上首页每次 page_view 同时 POST
        /vo5w/ga/g/c?tid=G-P6BH500VBK   和   ?tid=G-GECBME3YVJ
    两条共用同一个 gtm= 配置哈希与 cid —— 即同一个配置里的两个目的地。
    根因在 gtag.js 载荷里的 __dest_ga 有两个 destinationId（见
    _fetch_gtag_destinations 的注释）。

    predeploy_quality_gate 旧正则只匹配 gtag/js?id=（加载脚本），
    而第二个 ID 出现在 collect 路径 tid= 里 —— 所以 reports/quality/
    predeploy_quality.json（2026-09-14）显示 0 issues，闸门"通过"，
    双计在 main 分支上跑了 6 天无人拦截。

    后果是 users_28d / sessions_28d / engagement_rate_28d 全部双计，
    而这三个数当时正被 reporting_kpi_engine 当 LIVE KPI 上报。
    一个"看起来干净"的错误数字比显示 0 更危险。

    本检查把结果写成 reports/quality/analytics_posture.json，
    reporting_kpi_engine 读它把 GA4 来源的 KPI 标成 CONTAMINATED_SOURCE。
    """
    issues = []
    # 注意：不能用 REPORTS_DIR（那是 reports/site_health），姿态文件要和
    # predeploy_quality.json 放一起，reporting_kpi_engine 从那里读。
    posture_file = ROOT / "reports" / "quality" / "analytics_posture.json"

    # 第 1 层：页面 HTML 里显式出现几个 ID（抓「仓库里写了两个 gtag」这种常见情形）
    found_by_page, failed_pages, html_ids = {}, [], []
    for page_path in CHECK_PAGES:
        resp, html = _fetch_url(SITE_BASE_URL + page_path)
        if resp is None or not html:
            failed_pages.append(page_path)
            continue
        ids = sorted(set(re.findall(r"\bG-[A-Z0-9]{8,12}\b", " ".join(html.split()))))
        found_by_page[page_path] = ids
        html_ids.extend(ids)

    # 第 2 层：gtag.js 载荷里实际配置了几个目的地（抓 Google 侧的多目的地配置）
    gtag_payload = {}
    payload_dests = []
    for mid in sorted(set(html_ids)):
        try:
            dests, plen = _fetch_gtag_destinations(mid)
        except Exception:
            dests, plen = [], 0
        gtag_payload[mid] = {"destinations": dests, "payload_bytes": plen}
        payload_dests.extend(dests)

    all_ids = sorted(set(html_ids) | set(payload_dests))
    duplicated = len(all_ids) > 1

    if duplicated:
        issues.append({
            "type": "multiple_analytics_destinations",
            "severity": "critical",
            "check": "analytics_measurement_ids",
            "file": SITE_BASE_URL,
            "message": (
                f"GA4 的 Google Tag 配了 {len(all_ids)} 个目的地: "
                f"{', '.join(all_ids)}。每个事件会被同时记到所有目的地上。"
                "注意：单个属性的数值本身没被双计（各记一次），真实危害是 "
                "(1) 每次事件双倍开销与 API 配额，(2) 同一批访问行为存在于两个"
                "属性里，受众/再营销名单被重复灌入、两边看板对不上，"
                "(3) 仓库曾没有地方声明哪个属性是 canonical —— 现已补上"
                "config/analytics_canonical.json，第 3 层校验会检查"
                "hugo.toml / GA4_PROPERTY_ID / canonical 声明三方一致性"
                "（结果见 posture 的 config_mismatch 字段）。"
                "根因通常是 Google Tag Manager 里的一个 Google Tag 配了多个"
                "destinationId（本案例的页面 HTML 只有 1 个 ID，重复来自 "
                "gtag.js 载荷服务端配置），也可能只是仓库里写了两个 gtag。"
                "修法是删掉多余的 destination，仓库里改代码修不了。"
            ),
            "evidence": json.dumps({
                "html_ids_by_page": found_by_page,
                "gtag_payload": gtag_payload,
            }, ensure_ascii=False),
            "auto_fixable": False,
            "agent": "site_health",
        })

    # 第 3 层：配置一致性 —— 仓库里两套编号（measurement ID / property ID）
    # 必须指向同一个属性。这一层不看线上，只看仓库内配置是否自相矛盾。
    canonical = _load_analytics_canonical_config()
    config_mismatch, config_detail = _check_analytics_config_consistency(canonical)

    if config_mismatch:
        reasons = "; ".join(config_detail.get("mismatch_reasons", []))
        issues.append({
            "type": "analytics_config_inconsistency",
            "severity": "critical",
            "check": "analytics_measurement_ids",
            "file": "config/analytics_canonical.json",
            "message": (
                "GA4 配置不一致：" + reasons + "。"
                "仓库里 measurement ID（hugo.toml）和 property ID（GA4_PROPERTY_ID）"
                "曾分属两个不同的属性 —— 旧配置让所有报表脚本读的是重复属性，"
                "而站点的 gtag 指向另一个。修法是让两处都指向 canonical。"
            ),
            "evidence": json.dumps(config_detail, ensure_ascii=False),
            "auto_fixable": False,
            "agent": "site_health",
        })

    posture_file.parent.mkdir(parents=True, exist_ok=True)
    posture_file.write_text(json.dumps({
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "base_url": SITE_BASE_URL,
        "pages_checked": list(found_by_page.keys()),
        "pages_fetch_failed": failed_pages,
        "html_measurement_ids": sorted(set(html_ids)),
        "gtag_payload": gtag_payload,
        "measurement_ids": all_ids,
        "destination_count": len(all_ids),
        # duplicate_destinations 是规范字段名；contaminated 是首版遗留名，
        # 读取方（reporting_kpi_engine）两者都认，保留以免对不上。
        "duplicate_destinations": duplicated,
        "contaminated": duplicated,
        "canonical_config": config_detail,
        "config_mismatch": config_mismatch,
        "note": (
            "duplicate_destinations=True 表示 GA4 的 Google Tag 配了多个目的地，"
            "每个事件被记到多个属性里。单个属性的数值本身没有被双计，"
            "受影响的是来源的权威地位：受影响的流量 KPI"
            "（users_28d / sessions_28d / pageviews_28d / engagement_rate_28d）"
            "无法证明读的是 canonical 属性。"
            "根因在 Google 控制台的 tag 配置（gtag.js 载荷服务端生成），"
            "不在本仓库，也不在 Cloudflare —— 改仓库代码修不了它。"
        ),
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    return issues



def run_health_check(auto_fix=True):
    """运行完整健康检查"""
    ensure_dirs()
    timestamp = datetime.now(timezone.utc).isoformat()
    
    print("=" * 60)
    print("Site Health Agent - ChinaBound Travel 2.1")
    print("=" * 60)
    
    all_issues = []
    
    # 1. Sitemap健康检查
    print("\n[1/16] 检查Sitemap健康...")
    issues = check_sitemap_health()
    print(f"  发现 {len(issues)} 个问题")
    all_issues.extend(issues)
    
    # 2. Meta/Robots检查
    print("\n[2/16] 检查Meta/Robots配置...")
    issues = check_meta_robots()
    print(f"  发现 {len(issues)} 个问题")
    all_issues.extend(issues)
    
    # 3. 文件编码检查
    print("\n[3/16] 检查文件编码和乱码...")
    issues = check_file_encoding()
    print(f"  发现 {len(issues)} 个问题")
    all_issues.extend(issues)
    
    # 4. 内容占位符检查
    print("\n[4/16] 检查内容占位符...")
    issues = check_content_placeholders()
    print(f"  发现 {len(issues)} 个问题")
    all_issues.extend(issues)
    
    # 5. 工作流配置一致性
    print("\n[5/16] 检查工作流配置一致性...")
    issues = check_workflow_env_consistency()
    print(f"  发现 {len(issues)} 个问题")
    all_issues.extend(issues)
    
    # 6. 空链接检查
    print("\n[6/16] 检查空链接...")
    issues = check_empty_links()
    print(f"  发现 {len(issues)} 个问题")
    all_issues.extend(issues)
    
    # 7. 图片alt检查
    print("\n[7/16] 检查图片alt属性...")
    issues = check_image_alt()
    print(f"  发现 {len(issues)} 个问题")
    all_issues.extend(issues)
    
    # 8. 草稿泄露检查
    print("\n[8/16] 检查草稿泄露...")
    issues = check_draft_leak()
    print(f"  发现 {len(issues)} 个问题")
    all_issues.extend(issues)
    
    # 9. Persona违规检查
    print("\n[9/16] 检查Persona违规...")
    issues = check_persona_violation()
    print(f"  发现 {len(issues)} 个问题")
    all_issues.extend(issues)
    
    # 10. AI禁用词检查
    print("\n[10/16] 检查AI禁用词...")
    issues = check_ai_forbidden_words()
    print(f"  发现 {len(issues)} 个问题")
    all_issues.extend(issues)
    
    # 11. Title/Meta长度检查
    print("\n[11/16] 检查Title/Meta长度...")
    issues = check_title_meta_length()
    print(f"  发现 {len(issues)} 个问题")
    all_issues.extend(issues)
    
    # 以下为网络检查（需要联网，较慢）
    print("\n--- 网络检查（需要联网）---")
    
    # 12. 安全头检查
    print("\n[12/16] 检查安全头...")
    try:
        issues = check_security_headers()
        print(f"  发现 {len(issues)} 个问题")
        all_issues.extend(issues)
    except Exception as e:
        print(f"  ⚠️ 安全头检查失败: {e}")
        record_check_failure(all_issues, "security_headers", "安全头检查", e)
    
    # 12b. CSP 放行检查（与 12 分开：头存在不等于头内容够用）
    print("\n[12b/16] 检查 CSP 放行策略...")
    try:
        issues = check_csp_allowlist()
        print(f"  发现 {len(issues)} 个问题")
        all_issues.extend(issues)
    except Exception as e:
        print(f"  ⚠️ CSP 放行检查失败: {e}")
        record_check_failure(all_issues, "csp_allowlist", "CSP 放行检查", e)
    
    # 13. 混合内容检查
    print("\n[13/16] 检查混合内容...")
    try:
        issues = check_mixed_content()
        print(f"  发现 {len(issues)} 个问题")
        all_issues.extend(issues)
    except Exception as e:
        print(f"  ⚠️ 混合内容检查失败: {e}")
        record_check_failure(all_issues, "mixed_content", "混合内容检查", e)
    
    # 13b. GA4 measurement ID 双计检查（写 analytics_posture.json）
    print("\n[13b/16] 检查 GA4 measurement ID 是否被重复加载...")
    try:
        issues = check_analytics_measurement_ids()
        print(f"  发现 {len(issues)} 个问题")
        all_issues.extend(issues)
    except Exception as e:
        print(f"  ⚠️ GA4 双计检查失败: {e}")
        record_check_failure(all_issues, "analytics_measurement_ids", "GA4 双计检查", e)

    # 14. OG/Twitter标签检查
    print("\n[14/16] 检查OG/Twitter标签...")
    try:
        issues = check_og_tags()
        print(f"  发现 {len(issues)} 个问题")
        all_issues.extend(issues)
    except Exception as e:
        print(f"  ⚠️ OG标签检查失败: {e}")
        record_check_failure(all_issues, "og_tags", "OG标签检查", e)
    
    # 15. SSL证书检查
    print("\n[15/16] 检查SSL证书...")
    try:
        issues = check_ssl_certificate()
        print(f"  发现 {len(issues)} 个问题")
        all_issues.extend(issues)
    except Exception as e:
        print(f"  ⚠️ SSL检查失败: {e}")
        record_check_failure(all_issues, "ssl_certificate", "SSL证书检查", e)
    
    # 16. 结构化数据检查
    print("\n[16/16] 检查结构化数据...")
    try:
        issues = check_structured_data()
        print(f"  发现 {len(issues)} 个问题")
        all_issues.extend(issues)
    except Exception as e:
        print(f"  ⚠️ 结构化数据检查失败: {e}")
        record_check_failure(all_issues, "structured_data", "结构化数据检查", e)
    
    # 按严重程度排序
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    all_issues.sort(key=lambda x: severity_order.get(x["severity"], 99))
    
    # 继承历史已解决状态（避免重复报告已解决的问题）
    resolved_history = load_resolved_issues()
    inherited_count = 0
    for issue in all_issues:
        key = f"{issue.get('type','')}|{issue.get('page','')}|{issue.get('message','')[:50]}"
        if key in resolved_history and not issue.get("status"):
            hist = resolved_history[key]
            issue["status"] = hist["status"]
            issue["resolved_by"] = hist["resolved_by"]
            issue["resolution_note"] = hist["resolution_note"]
            issue["resolved_at"] = hist["resolved_at"]
            inherited_count += 1
    if inherited_count > 0:
        print(f"\n  [状态继承] {inherited_count} 个问题继承历史已解决状态，不计入未解决")
    
    # 自动修复
    fixed_issues = []
    if auto_fix:
        print("\n" + "=" * 60)
        print("自动修复 (L2权限)")
        print("=" * 60)
        for issue in all_issues:
            if issue.get("auto_fixable"):
                success, message = auto_fix_issue(issue)
                issue["fix_status"] = "fixed" if success else "failed"
                issue["fix_message"] = message
                fixed_issues.append(issue)
                status = "✅" if success else "❌"
                print(f"  {status} [{issue['severity']}] {issue['type']}: {message}")
    
    # 生成报告（只统计未解决问题）
    RESOLVED_STATUSES = {"resolved", "fixed", "false_positive", "closed"}
    unresolved = [i for i in all_issues if (i.get("status") or "").lower() not in RESOLVED_STATUSES]
    resolved_count = len(all_issues) - len(unresolved)
    
    report = {
        "timestamp": timestamp,
        "agent": "site_health",
        "permission_level": "L2",
        "summary": {
            "total_issues": len(unresolved),
            "critical": len([i for i in unresolved if i["severity"] == "critical"]),
            "high": len([i for i in unresolved if i["severity"] == "high"]),
            "medium": len([i for i in unresolved if i["severity"] == "medium"]),
            "low": len([i for i in unresolved if i["severity"] == "low"]),
            "auto_fixed": len([i for i in fixed_issues if i.get("fix_status") == "fixed"]),
            "need_manual": len([i for i in unresolved if not i.get("auto_fixable") or i.get("fix_status") == "failed"]),
            "resolved": resolved_count,
            "inherited_resolved": inherited_count
        },
        "issues": all_issues
    }
    
    # 保存报告
    report_file = REPORTS_DIR / f"site_health_{datetime.now().strftime('%Y-%m-%d')}.json"
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n报告已保存: {report_file.relative_to(ROOT)}")
    
    # 输出未修复问题到daily_issues格式（供router分配，排除已解决的）
    unresolved = [i for i in unresolved if not i.get("auto_fixable") or i.get("fix_status") == "failed"]
    if unresolved:
        issues_file = ISSUES_DIR / f"site_health_issues_{datetime.now().strftime('%Y-%m-%d')}.json"
        issues_file.write_text(json.dumps({
            "timestamp": timestamp,
            "source": "site_health_agent",
            "issues": unresolved
        }, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"未修复问题已输出: {issues_file.relative_to(ROOT)}")
    
    # 打印总结
    print("\n" + "=" * 60)
    print("检查总结")
    print("=" * 60)
    print(f"  未解决问题: {len(unresolved)} (历史已解决: {resolved_count})")
    print(f"  Critical: {report['summary']['critical']}")
    print(f"  High: {report['summary']['high']}")
    print(f"  Medium: {report['summary']['medium']}")
    print(f"  Low: {report['summary']['low']}")
    print(f"  本次自动修复: {report['summary']['auto_fixed']}")
    print(f"  需人工处理: {report['summary']['need_manual']}")
    
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Site Health Agent")
    parser.add_argument("--no-fix", action="store_true", help="只检查不修复")
    parser.add_argument("--check", type=str, help="只运行指定检查: sitemap|meta|encoding|content|workflow")
    args = parser.parse_args()
    
    run_health_check(auto_fix=not args.no_fix)
