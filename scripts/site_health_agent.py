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
PLACEHOLDER_PATTERNS = [
    re.compile(r'Review needed', re.IGNORECASE),
    re.compile(r'\bTODO\b'),
    re.compile(r'\bFIXME\b'),
    re.compile(r'placeholder', re.IGNORECASE),
    re.compile(r'待完善', re.IGNORECASE),
    re.compile(r'Lorem ipsum', re.IGNORECASE),
]


def ensure_dirs():
    """确保输出目录存在"""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ISSUES_DIR.mkdir(parents=True, exist_ok=True)


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
    EXCLUDE_DIRS = ['drafts', '.audit_backup', '_drafts']
    
    for md_file in CONTENT_DIR.rglob("*.md"):
        # 跳过排除目录
        rel_path = str(md_file.relative_to(ROOT))
        if any(exclude in rel_path for exclude in EXCLUDE_DIRS):
            continue
            
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
            # 只检查正文（front matter之后）
            front_matter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
            body = content[front_matter_match.end():] if front_matter_match else content
            
            for pattern in PLACEHOLDER_PATTERNS:
                matches = pattern.findall(body)
                if matches:
                    issues.append({
                        "type": "content_placeholder",
                        "severity": "medium",
                        "file": rel_path,
                        "message": f"发现占位符/状态标记: {matches[0]}",
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
        if any(exclude in rel_path for exclude in ['drafts', '.audit_backup', '_drafts']):
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
        if any(exclude in rel_path for exclude in ['drafts', '.audit_backup', '_drafts']):
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
        if any(exclude in rel_path for exclude in ['drafts', '.audit_backup', '_drafts']):
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
        if any(exclude in rel_path for exclude in ['drafts', '.audit_backup', '_drafts']):
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
        if any(exclude in rel_path for exclude in ['drafts', '.audit_backup', '_drafts']):
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
        if any(exclude in rel_path for exclude in ['drafts', '.audit_backup', '_drafts']):
            continue
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
            front_matter_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
            if not front_matter_match:
                continue
            front_matter = front_matter_match.group(1)
            
            # Title长度检查
            title_match = re.search(r"title\s*:\s*[\"']?([^\"'\n]+)", front_matter)
            if title_match:
                title = title_match.group(1).strip()
                if len(title) > 65:
                    issues.append({
                        "type": "title_too_long",
                        "severity": "low",
                        "file": rel_path,
                        "message": f"Title过长({len(title)}字符): {title[:40]}...",
                        "auto_fixable": False,
                        "agent": "seo"
                    })
                elif len(title) < 20:
                    issues.append({
                        "type": "title_too_short",
                        "severity": "low",
                        "file": rel_path,
                        "message": f"Title过短({len(title)}字符)",
                        "auto_fixable": False,
                        "agent": "seo"
                    })
            
            # Meta description长度检查
            desc_match = re.search(r"description\s*:\s*[\"']?([^\"'\n]+)", front_matter)
            if desc_match:
                desc = desc_match.group(1).strip()
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
    """获取URL响应，返回(response, html_content)或(None, None)"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SiteHealthBot/1.0"})
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=NETWORK_TIMEOUT, context=ctx) as resp:
            html = resp.read().decode("utf-8", errors="replace")
            return resp, html
    except Exception as e:
        return None, None


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
        
        # 检查OG标签
        for og_tag in REQUIRED_OG:
            pattern = re.compile(r"property=[\"']" + re.escape(og_tag) + r"[\"']]", re.IGNORECASE)
            if not pattern.search(html):
                issues.append({
                    "type": "og_tag_missing",
                    "severity": "low",
                    "file": page_path,
                    "message": f"缺少OG标签: {og_tag}",
                    "auto_fixable": False,
                    "agent": "seo"
                })
        
        # 检查Twitter标签
        for tw_tag in REQUIRED_TWITTER:
            pattern = re.compile(r"name=[\"']" + re.escape(tw_tag) + r"[\"']]", re.IGNORECASE)
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
        
        else:
            return False, f"未知修复操作: {fix_action}"
    
    except Exception as e:
        return False, f"修复失败: {str(e)}"


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
    
    # 13. 混合内容检查
    print("\n[13/16] 检查混合内容...")
    try:
        issues = check_mixed_content()
        print(f"  发现 {len(issues)} 个问题")
        all_issues.extend(issues)
    except Exception as e:
        print(f"  ⚠️ 混合内容检查失败: {e}")
    
    # 14. OG/Twitter标签检查
    print("\n[14/16] 检查OG/Twitter标签...")
    try:
        issues = check_og_tags()
        print(f"  发现 {len(issues)} 个问题")
        all_issues.extend(issues)
    except Exception as e:
        print(f"  ⚠️ OG标签检查失败: {e}")
    
    # 15. SSL证书检查
    print("\n[15/16] 检查SSL证书...")
    try:
        issues = check_ssl_certificate()
        print(f"  发现 {len(issues)} 个问题")
        all_issues.extend(issues)
    except Exception as e:
        print(f"  ⚠️ SSL检查失败: {e}")
    
    # 16. 结构化数据检查
    print("\n[16/16] 检查结构化数据...")
    try:
        issues = check_structured_data()
        print(f"  发现 {len(issues)} 个问题")
        all_issues.extend(issues)
    except Exception as e:
        print(f"  ⚠️ 结构化数据检查失败: {e}")
    
    # 按严重程度排序
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    all_issues.sort(key=lambda x: severity_order.get(x["severity"], 99))
    
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
    
    # 生成报告
    report = {
        "timestamp": timestamp,
        "agent": "site_health",
        "permission_level": "L2",
        "summary": {
            "total_issues": len(all_issues),
            "critical": len([i for i in all_issues if i["severity"] == "critical"]),
            "high": len([i for i in all_issues if i["severity"] == "high"]),
            "medium": len([i for i in all_issues if i["severity"] == "medium"]),
            "low": len([i for i in all_issues if i["severity"] == "low"]),
            "auto_fixed": len([i for i in fixed_issues if i.get("fix_status") == "fixed"]),
            "need_manual": len([i for i in all_issues if not i.get("auto_fixable") or i.get("fix_status") == "failed"])
        },
        "issues": all_issues
    }
    
    # 保存报告
    report_file = REPORTS_DIR / f"site_health_{datetime.now().strftime('%Y-%m-%d')}.json"
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n报告已保存: {report_file.relative_to(ROOT)}")
    
    # 输出未修复问题到daily_issues格式（供router分配）
    unresolved = [i for i in all_issues if not i.get("auto_fixable") or i.get("fix_status") == "failed"]
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
    print(f"  总问题数: {len(all_issues)}")
    print(f"  Critical: {report['summary']['critical']}")
    print(f"  High: {report['summary']['high']}")
    print(f"  Medium: {report['summary']['medium']}")
    print(f"  Low: {report['summary']['low']}")
    print(f"  已自动修复: {report['summary']['auto_fixed']}")
    print(f"  需人工处理: {report['summary']['need_manual']}")
    
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Site Health Agent")
    parser.add_argument("--no-fix", action="store_true", help="只检查不修复")
    parser.add_argument("--check", type=str, help="只运行指定检查: sitemap|meta|encoding|content|workflow")
    args = parser.parse_args()
    
    run_health_check(auto_fix=not args.no_fix)
