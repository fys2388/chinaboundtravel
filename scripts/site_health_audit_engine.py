#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChinaBound Travel - Site Health Audit Engine v1.0
网站健康审计引擎（主动审计层，与 Learning Loop 互补）

6大审计模块：
1. Security/Config Audit - CSP、安全头、分析工具、Sentry
2. Conversion Funnel Audit - 联系表单、CTA、社交证明、表单方法
3. Technical SEO Audit - 结构化数据、标题、Meta、canonical
4. Content Quality Audit - 字数、配图、AI痕迹、内容重叠
5. UX/Design Audit - 导航、面包屑、页脚、视觉元素
6. IA Audit - 信息架构、内容重叠、标签页、搜索

与 Learning Loop 的区别：
- Learning Loop = 被动学习（等数据积累后发现异常）
- Site Health Audit = 主动审计（直接检查配置/结构/质量缺陷）
"""
from __future__ import annotations

import os
import sys
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

import requests

# 项目配置
PROJECT_ROOT = Path(__file__).parent.parent
SITE_URL = "https://www.chinaboundtravel.com"
REPORTS_DIR = PROJECT_ROOT / "reports" / "site_health"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

CONTENT_DIR = PROJECT_ROOT / "content"
LAYOUTS_DIR = PROJECT_ROOT / "layouts"
CONFIG_FILE = PROJECT_ROOT / "hugo.toml"
PUBLIC_DIR = PROJECT_ROOT / "public"

# 审计结果等级
SEVERITY_CRITICAL = "CRITICAL"
SEVERITY_HIGH = "HIGH"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_LOW = "LOW"
SEVERITY_INFO = "INFO"


class AuditFinding:
    """审计发现"""
    def __init__(self, module: str, severity: str, title: str, description: str,
                 location: str = "", recommendation: str = "", auto_fixable: bool = False):
        self.module = module
        self.severity = severity
        self.title = title
        self.description = description
        self.location = location
        self.recommendation = recommendation
        self.auto_fixable = auto_fixable
        self.found_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "module": self.module,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "recommendation": self.recommendation,
            "auto_fixable": self.auto_fixable,
            "found_at": self.found_at,
        }


class SiteHealthAuditor:
    """网站健康审计器"""

    def __init__(self):
        self.findings: List[AuditFinding] = []
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "ChinaBound-SiteHealthAudit/1.0"})
        self._cache = {}

    def add_finding(self, **kwargs):
        self.findings.append(AuditFinding(**kwargs))

    def fetch_url(self, url: str, timeout: int = 15) -> Optional[requests.Response]:
        """获取 URL 响应（带缓存）"""
        if url in self._cache:
            return self._cache[url]
        try:
            r = self.session.get(url, timeout=timeout, allow_redirects=True)
            self._cache[url] = r
            return r
        except Exception as e:
            print(f"  ⚠️ 获取 {url} 失败: {e}")
            return None

    # ============================================================
    # 模块1: Security/Config Audit
    # ============================================================
    def audit_security_config(self):
        """安全与配置审计"""
        print("\n" + "=" * 60)
        print("  模块1: Security/Config Audit")
        print("=" * 60)

        # 1.1 检查安全头
        print("  📋 检查安全响应头...")
        r = self.fetch_url(SITE_URL)
        if r:
            headers = r.headers
            required_headers = {
                "Strict-Transport-Security": "HSTS",
                "Content-Security-Policy": "CSP",
                "X-Content-Type-Options": "MIME类型嗅探防护",
                "X-Frame-Options": "点击劫持防护",
                "Referrer-Policy": "Referrer策略",
                "Permissions-Policy": "权限策略",
            }
            for header, desc in required_headers.items():
                if header not in headers:
                    self.add_finding(
                        module="security",
                        severity=SEVERITY_MEDIUM,
                        title=f"缺少安全头: {header}",
                        description=f"网站未设置 {header} 响应头（{desc}）",
                        location=SITE_URL,
                        recommendation=f"在 Cloudflare 或服务器配置中添加 {header} 响应头",
                        auto_fixable=True,
                    )
                else:
                    print(f"    ✅ {header}: 已配置")

            # 1.2 检查 CSP 是否拦截关键服务
            csp = headers.get("Content-Security-Policy", "")
            if csp:
                print("  📋 检查 CSP 策略...")
                critical_services = {
                    "sentry.io": "Sentry 错误追踪",
                    "sentry.avs.io": "Sentry 错误追踪（自定义域名）",
                    "googlesyndication.com": "Google AdSense",
                    "google-analytics.com": "Google Analytics",
                    "googletagmanager.com": "Google Tag Manager",
                    "cloudflareinsights.com": "Cloudflare Analytics",
                }
                for domain, desc in critical_services.items():
                    if domain not in csp:
                        # 检查是否在 connect-src 或 script-src 中
                        if "connect-src" in csp and domain not in csp.split("connect-src")[1].split(";")[0] if "connect-src" in csp else True:
                            self.add_finding(
                                module="security",
                                severity=SEVERITY_HIGH,
                                title=f"CSP 未允许 {desc}",
                                description=f"Content-Security-Policy 中未包含 {domain}，可能导致 {desc} 被拦截",
                                location=f"CSP: {csp[:200]}...",
                                recommendation=f"在 CSP 的 connect-src 和/或 script-src 中添加 {domain}",
                                auto_fixable=True,
                            )
                            print(f"    ❌ {domain}: 未在 CSP 中（{desc} 可能被拦截）")
                    else:
                        print(f"    ✅ {domain}: 已在 CSP 中")

        # 1.3 检查分析工具配置
        print("  📋 检查分析工具...")
        analytics_tools = {
            "GA4": {"check": "googletagmanager.com/gtag/js", "desc": "Google Analytics 4"},
            "Cloudflare Analytics": {"check": "static.cloudflareinsights.com", "desc": "Cloudflare Web Analytics"},
            "Sentry": {"check": "sentry.io", "desc": "Sentry 错误追踪"},
        }
        if r:
            html = r.text
            for tool, config in analytics_tools.items():
                if config["check"] in html:
                    print(f"    ✅ {tool}: 已配置")
                else:
                    self.add_finding(
                        module="security",
                        severity=SEVERITY_HIGH if tool == "Cloudflare Analytics" else SEVERITY_MEDIUM,
                        title=f"缺少分析工具: {tool}",
                        description=f"网站未配置 {tool}（{config['desc']}）",
                        location=SITE_URL,
                        recommendation=f"添加 {tool} 脚本到网站头部",
                        auto_fixable=True,
                    )
                    print(f"    ❌ {tool}: 未配置")

        # 1.4 检查 HTTPS 和 WWW 重定向
        print("  📋 检查重定向...")
        for test_url in ["http://chinaboundtravel.com", "https://chinaboundtravel.com"]:
            r2 = self.fetch_url(test_url, timeout=10)
            if r2 and r2.url != test_url:
                print(f"    ✅ {test_url} → {r2.url}")
            elif r2 and r2.status_code == 200 and test_url != SITE_URL:
                self.add_finding(
                    module="security",
                    severity=SEVERITY_MEDIUM,
                    title=f"未重定向到规范域名: {test_url}",
                    description=f"{test_url} 未重定向到 {SITE_URL}，可能导致重复内容和 SEO 问题",
                    location=test_url,
                    recommendation="配置 301 重定向到 www.chinaboundtravel.com",
                    auto_fixable=True,
                )
                print(f"    ❌ {test_url}: 未重定向")

        print(f"  📊 安全/配置审计完成: {sum(1 for f in self.findings if f.module == 'security')} 个发现")

    # ============================================================
    # 模块2: Conversion Funnel Audit
    # ============================================================
    def audit_conversion_funnel(self):
        """转化漏斗审计"""
        print("\n" + "=" * 60)
        print("  模块2: Conversion Funnel Audit")
        print("=" * 60)

        # 2.1 检查联系页面
        print("  📋 检查联系页面...")
        contact_url = f"{SITE_URL}/contact/"
        r = self.fetch_url(contact_url)
        if r and r.status_code == 200:
            html = r.text
            # 检查是否有真正的联系表单
            has_form = bool(re.search(r'<form[^>]*>', html, re.I))
            has_formspree = "formspree" in html.lower()
            has_mailto = "mailto:" in html
            has_input = bool(re.search(r'<input[^>]*type=["\']?(text|email|name)', html, re.I))

            if not has_form and not has_formspree:
                self.add_finding(
                    module="conversion",
                    severity=SEVERITY_HIGH,
                    title="联系页面缺少联系表单",
                    description="联系页面没有真正的联系表单，用户需要手动打开邮件客户端发送邮件，转化漏斗断裂",
                    location=contact_url,
                    recommendation="添加 Formspree 或类似服务的联系表单，支持用户直接在页面提交",
                    auto_fixable=True,
                )
                print("    ❌ 联系表单: 缺失")
            else:
                print("    ✅ 联系表单: 已存在")

            if has_mailto and not has_form:
                print("    ⚠️ 仅使用 mailto 链接（用户体验差）")

            # 检查表单方法
            if has_form:
                form_match = re.search(r'<form[^>]*method=["\']?(\w+)', html, re.I)
                if form_match and form_match.group(1).upper() == "GET":
                    self.add_finding(
                        module="conversion",
                        severity=SEVERITY_MEDIUM,
                        title="表单使用 GET 方法",
                        description="联系表单使用 GET 方法提交，邮箱地址会暴露在 URL 中，不规范且不利于追踪",
                        location=contact_url,
                        recommendation="将表单方法改为 POST",
                        auto_fixable=True,
                    )
                    print("    ❌ 表单方法: GET（应改为 POST）")
        else:
            self.add_finding(
                module="conversion",
                severity=SEVERITY_HIGH,
                title="联系页面无法访问",
                description=f"联系页面 {contact_url} 返回状态码 {r.status_code if r else 'N/A'}",
                location=contact_url,
                recommendation="检查联系页面是否存在且可访问",
                auto_fixable=False,
            )

        # 2.2 检查内页 CTA
        print("  📋 检查内页 CTA...")
        # 检查几篇代表性博客文章
        sample_posts = [
            f"{SITE_URL}/posts/china-travel-tips/",
            f"{SITE_URL}/posts/china-visa-guide/",
            f"{SITE_URL}/posts/alipay-china/",
        ]
        weak_cta_pages = []
        for post_url in sample_posts:
            r = self.fetch_url(post_url)
            if r and r.status_code == 200:
                html = r.text
                # 检查文章底部是否有 CTA
                cta_patterns = [r'class=["\'][^"\']*cta[^"\']*["\']', r'class=["\'][^"\']*newsletter[^"\']*["\']',
                                r'class=["\'][^"\']*affiliate[^"\']*["\']', r'class=["\'][^"\']*related[^"\']*["\']']
                has_cta = any(re.search(p, html, re.I) for p in cta_patterns)
                if not has_cta:
                    weak_cta_pages.append(post_url)

        if weak_cta_pages:
            self.add_finding(
                module="conversion",
                severity=SEVERITY_MEDIUM,
                title="内页 CTA 较弱",
                description=f"以下 {len(weak_cta_pages)} 篇博客文章底部缺少明确的 CTA（邮件订阅/联盟推荐/相关文章）",
                location=", ".join(weak_cta_pages),
                recommendation="在每篇博客底部添加与内容相关的个性化 CTA（如签证文章→签证清单PDF）",
                auto_fixable=True,
            )
            print(f"    ❌ 弱 CTA 页面: {len(weak_cta_pages)} 个")
        else:
            print("    ✅ 内页 CTA: 正常")

        # 2.3 检查社交证明
        print("  📋 检查社交证明...")
        r = self.fetch_url(SITE_URL)
        if r:
            html = r.text
            social_proof_patterns = [r'testimonial', r'review', r'rating', r'subscriber', r'customer', r'user.*say']
            has_social_proof = any(re.search(p, html, re.I) for p in social_proof_patterns)
            if not has_social_proof:
                self.add_finding(
                    module="conversion",
                    severity=SEVERITY_MEDIUM,
                    title="缺少社交证明",
                    description="首页和定价页缺少用户评价、推荐语、真实订阅人数等社交证明元素",
                    location=SITE_URL,
                    recommendation="收集用户评价/推荐语，展示在定价页和首页；添加真实订阅人数",
                    auto_fixable=False,
                )
                print("    ❌ 社交证明: 缺失")
            else:
                print("    ✅ 社交证明: 已存在")

        print(f"  📊 转化漏斗审计完成: {sum(1 for f in self.findings if f.module == 'conversion')} 个发现")

    # ============================================================
    # 模块3: Technical SEO Audit
    # ============================================================
    def audit_technical_seo(self):
        """技术 SEO 审计"""
        print("\n" + "=" * 60)
        print("  模块3: Technical SEO Audit")
        print("=" * 60)

        # 3.1 检查结构化数据
        print("  📋 检查结构化数据...")
        r = self.fetch_url(SITE_URL)
        if r:
            html = r.text
            schema_types = re.findall(r'"@type"\s*:\s*"([^"]+)"', html)
            unique_types = list(set(schema_types))
            print(f"    发现的 Schema 类型: {unique_types}")

            required_schemas = {
                "WebSite": "网站搜索功能",
                "Organization": "组织信息",
                "BreadcrumbList": "面包屑导航",
            }
            for schema, desc in required_schemas.items():
                if schema not in unique_types:
                    self.add_finding(
                        module="seo",
                        severity=SEVERITY_HIGH if schema == "BreadcrumbList" else SEVERITY_MEDIUM,
                        title=f"缺少结构化数据: {schema}",
                        description=f"网站未包含 {schema} 结构化数据（{desc}），错失富摘要机会",
                        location=SITE_URL,
                        recommendation=f"在页面中添加 {schema} JSON-LD 结构化数据",
                        auto_fixable=True,
                    )
                    print(f"    ❌ {schema}: 缺失")
                else:
                    print(f"    ✅ {schema}: 已存在")

        # 3.2 检查博客文章的 Article schema
        print("  📋 检查博客文章结构化数据...")
        sample_post = f"{SITE_URL}/posts/china-travel-tips/"
        r = self.fetch_url(sample_post)
        if r and r.status_code == 200:
            html = r.text
            if '"@type":"Article"' not in html and '"@type": "Article"' not in html:
                self.add_finding(
                    module="seo",
                    severity=SEVERITY_HIGH,
                    title="博客文章缺少 Article 结构化数据",
                    description="博客文章页面未包含 Article/BlogPosting 结构化数据，影响搜索结果展示",
                    location=sample_post,
                    recommendation="在博客文章模板中添加 Article JSON-LD 结构化数据（含标题、作者、日期、图片）",
                    auto_fixable=True,
                )
                print("    ❌ Article schema: 缺失")
            else:
                print("    ✅ Article schema: 已存在")

        # 3.3 检查博客列表页标题
        print("  📋 检查博客列表页标题...")
        blog_url = f"{SITE_URL}/posts/"
        r = self.fetch_url(blog_url)
        if r and r.status_code == 200:
            html = r.text
            title_match = re.search(r'<title>([^<]+)</title>', html, re.I)
            if title_match:
                title = title_match.group(1).strip()
                print(f"    博客列表标题: {title}")
                if title.lower() in ["posts", "posts | chinabound travel", "blog"]:
                    self.add_finding(
                        module="seo",
                        severity=SEVERITY_MEDIUM,
                        title="博客列表页标题泛化",
                        description=f"博客列表页标题为 '{title}'，缺少关键词，应改为描述性标题如 'China Travel Guides & Tips | ChinaBound Travel'",
                        location=blog_url,
                        recommendation="优化博客列表页标题，包含核心关键词",
                        auto_fixable=True,
                    )
                    print("    ❌ 标题泛化: 需要优化")
        else:
            print(f"    ⚠️ 博客列表页无法访问: {r.status_code if r else 'N/A'}")

        # 3.4 检查 Meta 标签完整性
        print("  📋 检查 Meta 标签...")
        r = self.fetch_url(SITE_URL)
        if r:
            html = r.text
            meta_checks = {
                "meta description": r'<meta[^>]*name=["\']description["\']',
                "OG title": r'<meta[^>]*property=["\']og:title["\']',
                "OG description": r'<meta[^>]*property=["\']og:description["\']',
                "OG image": r'<meta[^>]*property=["\']og:image["\']',
                "Twitter card": r'<meta[^>]*name=["\']twitter:card["\']',
                "canonical": r'<link[^>]*rel=["\']canonical["\']',
            }
            for name, pattern in meta_checks.items():
                if not re.search(pattern, html, re.I):
                    self.add_finding(
                        module="seo",
                        severity=SEVERITY_MEDIUM,
                        title=f"缺少 Meta 标签: {name}",
                        description=f"首页缺少 {name} 标签",
                        location=SITE_URL,
                        recommendation=f"添加 {name} 标签",
                        auto_fixable=True,
                    )
                    print(f"    ❌ {name}: 缺失")
                else:
                    print(f"    ✅ {name}: 已存在")

        print(f"  📊 技术 SEO 审计完成: {sum(1 for f in self.findings if f.module == 'seo')} 个发现")

    # ============================================================
    # 模块4: Content Quality Audit
    # ============================================================
    def audit_content_quality(self):
        """内容质量审计"""
        print("\n" + "=" * 60)
        print("  模块4: Content Quality Audit")
        print("=" * 60)

        # 4.1 检查城市指南字数
        print("  📋 检查城市指南字数...")
        cities_dir = CONTENT_DIR / "cities"
        if cities_dir.exists():
            city_files = list(cities_dir.glob("*.md"))
            print(f"    发现 {len(city_files)} 个城市指南")
            for city_file in city_files[:8]:  # 检查前8个
                try:
                    text = city_file.read_text(encoding="utf-8", errors="replace")
                    # 移除 front matter
                    if text.startswith("---"):
                        parts = text.split("---", 2)
                        if len(parts) >= 3:
                            text = parts[2]
                    word_count = len(text.split())
                    if word_count < 1500:
                        self.add_finding(
                            module="content",
                            severity=SEVERITY_HIGH,
                            title=f"城市指南字数不足: {city_file.stem}",
                            description=f"城市指南 '{city_file.stem}' 仅 {word_count} 词，建议至少 1500-2000 词",
                            location=str(city_file.relative_to(PROJECT_ROOT)),
                            recommendation="扩写城市指南，添加景点推荐、行程规划、实用信息、FAQ",
                            auto_fixable=False,
                        )
                        print(f"    ❌ {city_file.stem}: {word_count} 词（不足）")
                    else:
                        print(f"    ✅ {city_file.stem}: {word_count} 词")
                except Exception as e:
                    print(f"    ⚠️ {city_file.stem}: 读取失败 - {e}")

        # 4.2 检查城市页配图
        print("  📋 检查城市页配图...")
        sample_cities = ["beijing", "shanghai", "chengdu"]
        for city in sample_cities:
            city_url = f"{SITE_URL}/cities/{city}/"
            r = self.fetch_url(city_url)
            if r and r.status_code == 200:
                html = r.text
                # 检查是否有实际内容图片（排除 logo、favicon、图标）
                img_matches = re.findall(r'<img[^>]*src=["\']([^"\']+)["\']', html, re.I)
                content_images = [src for src in img_matches if not any(x in src.lower() for x in ["logo", "favicon", "icon", "avatar", "gravatar"])]
                if len(content_images) < 2:
                    self.add_finding(
                        module="content",
                        severity=SEVERITY_HIGH,
                        title=f"城市页缺少配图: {city}",
                        description=f"城市页 '{city}' 仅有 {len(content_images)} 张内容图片，旅游网站应至少 3-5 张实际景点照片",
                        location=city_url,
                        recommendation="添加 3-5 张高质量的城市景点照片",
                        auto_fixable=False,
                    )
                    print(f"    ❌ {city}: {len(content_images)} 张内容图（不足）")
                else:
                    print(f"    ✅ {city}: {len(content_images)} 张内容图")

        # 4.3 检查 AI 写作痕迹
        print("  📋 检查 AI 写作痕迹...")
        posts_dir = CONTENT_DIR / "posts"
        if posts_dir.exists():
            post_files = list(posts_dir.glob("*.md"))[:5]  # 检查前5篇
            ai_patterns = [
                (r"It\'s like', '电影比喻模式化"),
                (r"in conclusion', '模板化结尾"),
                (r"it is important to note', 'AI套话"),
                (r"navigate the complexities', 'AI套话"),
                (r"delve into', 'AI套话"),
                (r"tapestry', 'AI套话"),
                (r"testament to', 'AI套话"),
            ]
            for post_file in post_files:
                try:
                    text = post_file.read_text(encoding="utf-8", errors="replace").lower()
                    ai_hits = sum(1 for pattern, _ in ai_patterns if re.search(pattern.lower(), text))
                    if ai_hits >= 3:
                        self.add_finding(
                            module="content",
                            severity=SEVERITY_MEDIUM,
                            title=f"AI 写作痕迹: {post_file.stem}",
                            description=f"文章 '{post_file.stem}' 检测到 {ai_hits} 个 AI 写作模式特征",
                            location=str(post_file.relative_to(PROJECT_ROOT)),
                            recommendation="人工编辑，减少模式化表达，增加个人经验和独特观点",
                            auto_fixable=False,
                        )
                        print(f"    ⚠️ {post_file.stem}: {ai_hits} 个 AI 特征")
                except Exception:
                    pass

        # 4.4 检查内容重叠
        print("  📋 检查内容重叠...")
        # 简单检查：城市页和博客是否有相同标题
        cities_dir = CONTENT_DIR / "cities"
        posts_dir = CONTENT_DIR / "posts"
        if cities_dir.exists() and posts_dir.exists():
            city_titles = {f.stem.lower().replace("-", " ") for f in cities_dir.glob("*.md")}
            overlapping = []
            for post in posts_dir.glob("*.md"):
                post_title = post.stem.lower().replace("-", " ")
                for city in city_titles:
                    if city in post_title or post_title in city:
                        overlapping.append((post.stem, city))
                        break
            if overlapping:
                self.add_finding(
                    module="content",
                    severity=SEVERITY_MEDIUM,
                    title="内容重叠: 博客 vs 城市页",
                    description=f"发现 {len(overlapping)} 组内容重叠，可能造成关键词内部竞争",
                    location=", ".join([f"{p}↔{c}" for p, c in overlapping[:5]]),
                    recommendation="明确区分博客和城市页的定位，或合并重复内容，设置 canonical",
                    auto_fixable=False,
                )
                print(f"    ❌ 内容重叠: {len(overlapping)} 组")

        print(f"  📊 内容质量审计完成: {sum(1 for f in self.findings if f.module == 'content')} 个发现")

    # ============================================================
    # 模块5: UX/Design Audit
    # ============================================================
    def audit_ux_design(self):
        """UX/设计审计"""
        print("\n" + "=" * 60)
        print("  模块5: UX/Design Audit")
        print("=" * 60)

        # 5.1 检查导航项数量
        print("  📋 检查导航结构...")
        r = self.fetch_url(SITE_URL)
        if r:
            html = r.text
            # 提取导航菜单项
            nav_items = re.findall(r'<nav[^>]*>.*?</nav>', html, re.DOTALL | re.I)
            if nav_items:
                nav_html = nav_items[0]
                nav_links = re.findall(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>', nav_html, re.I)
                nav_count = len(nav_links)
                print(f"    导航项数量: {nav_count}")
                if nav_count > 8:
                    self.add_finding(
                        module="ux",
                        severity=SEVERITY_MEDIUM,
                        title="导航栏菜单项过多",
                        description=f"导航栏有 {nav_count} 个菜单项，建议精简至 6-7 个，移动端会严重拥挤",
                        location=SITE_URL,
                        recommendation="合并相关菜单项（如 Visa/Payment/Internet 合并为 Essentials）",
                        auto_fixable=True,
                    )
                    print(f"    ❌ 导航过载: {nav_count} 项（建议≤8）")
                else:
                    print(f"    ✅ 导航数量: 正常")

        # 5.2 检查面包屑导航
        print("  📋 检查面包屑导航...")
        breadcrumb_template = LAYOUTS_DIR / "partials" / "breadcrumbs.html"
        if breadcrumb_template.exists():
            # 检查是否在页面中实际使用
            r = self.fetch_url(f"{SITE_URL}/posts/china-travel-tips/")
            if r and r.status_code == 200:
                html = r.text
                has_breadcrumb = bool(re.search(r'class=["\'][^"\']*breadcrumb', html, re.I))
                if not has_breadcrumb:
                    self.add_finding(
                        module="ux",
                        severity=SEVERITY_MEDIUM,
                        title="面包屑导航模板存在但未启用",
                        description="layouts/partials/breadcrumbs.html 存在，但页面中未实际渲染面包屑导航",
                        location=str(breadcrumb_template.relative_to(PROJECT_ROOT)),
                        recommendation="在文章/页面模板中引用 breadcrumbs.html  partial，并添加 BreadcrumbList 结构化数据",
                        auto_fixable=True,
                    )
                    print("    ❌ 面包屑: 模板存在但未启用")
                else:
                    print("    ✅ 面包屑: 已启用")
        else:
            self.add_finding(
                module="ux",
                severity=SEVERITY_LOW,
                title="缺少面包屑导航模板",
                description="网站没有面包屑导航模板",
                location=SITE_URL,
                recommendation="创建面包屑导航模板并在页面中使用",
                auto_fixable=True,
            )
            print("    ❌ 面包屑模板: 不存在")

        # 5.3 检查页脚
        print("  📋 检查页脚...")
        r = self.fetch_url(SITE_URL)
        if r:
            html = r.text
            footer_match = re.search(r'<footer[^>]*>(.*?)</footer>', html, re.DOTALL | re.I)
            if footer_match:
                footer_html = footer_match.group(1)
                if "hugo" in footer_html.lower() or "papermod" in footer_html.lower():
                    self.add_finding(
                        module="ux",
                        severity=SEVERITY_LOW,
                        title="页脚暴露技术栈",
                        description="页脚显示 'Powered by Hugo & PaperMod'，商业网站应移除或自定义",
                        location=SITE_URL,
                        recommendation="移除页脚的 Hugo/PaperMod 署名，改为自定义版权信息",
                        auto_fixable=True,
                    )
                    print("    ❌ 页脚: 暴露技术栈")
                else:
                    print("    ✅ 页脚: 已自定义")

        # 5.4 检查移动端视口
        print("  📋 检查移动端适配...")
        r = self.fetch_url(SITE_URL)
        if r:
            html = r.text
            viewport = re.search(r'<meta[^>]*name=["\']viewport["\'][^>]*>', html, re.I)
            if viewport:
                print("    ✅ viewport meta: 已配置")
            else:
                self.add_finding(
                    module="ux",
                    severity=SEVERITY_HIGH,
                    title="缺少 viewport meta 标签",
                    description="网站缺少 viewport meta 标签，移动端适配会出问题",
                    location=SITE_URL,
                    recommendation='添加 <meta name="viewport" content="width=device-width, initial-scale=1">',
                    auto_fixable=True,
                )
                print("    ❌ viewport: 缺失")

        print(f"  📊 UX/设计审计完成: {sum(1 for f in self.findings if f.module == 'ux')} 个发现")

    # ============================================================
    # 模块6: IA Audit
    # ============================================================
    def audit_ia(self):
        """信息架构审计"""
        print("\n" + "=" * 60)
        print("  模块6: IA Audit (信息架构)")
        print("=" * 60)

        # 6.1 检查内容分类
        print("  📋 检查内容分类...")
        if CONTENT_DIR.exists():
            content_dirs = [d.name for d in CONTENT_DIR.iterdir() if d.is_dir() and not d.name.startswith("_")]
            print(f"    内容分类: {content_dirs}")
            if len(content_dirs) > 12:
                self.add_finding(
                    module="ia",
                    severity=SEVERITY_LOW,
                    title="内容分类过多",
                    description=f"内容目录有 {len(content_dirs)} 个分类，建议精简合并",
                    location=str(CONTENT_DIR.relative_to(PROJECT_ROOT)),
                    recommendation="合并相关分类，减少用户认知负担",
                    auto_fixable=False,
                )

        # 6.2 检查 sitemap
        print("  📋 检查 sitemap...")
        sitemap_url = f"{SITE_URL}/sitemap.xml"
        r = self.fetch_url(sitemap_url)
        if r and r.status_code == 200:
            urls = re.findall(r'<loc>([^<]+)</loc>', r.text)
            print(f"    sitemap URL 数量: {len(urls)}")
            if len(urls) < 30:
                self.add_finding(
                    module="ia",
                    severity=SEVERITY_LOW,
                    title="sitemap URL 数量较少",
                    description=f"sitemap 仅包含 {len(urls)} 个 URL，内容量可能不足",
                    location=sitemap_url,
                    recommendation="持续增加高质量内容",
                    auto_fixable=False,
                )
        else:
            self.add_finding(
                module="ia",
                severity=SEVERITY_HIGH,
                title="sitemap.xml 无法访问",
                description=f"sitemap.xml 返回状态码 {r.status_code if r else 'N/A'}",
                location=sitemap_url,
                recommendation="检查 Hugo 是否生成 sitemap.xml",
                auto_fixable=True,
            )
            print("    ❌ sitemap: 无法访问")

        # 6.3 检查 robots.txt
        print("  📋 检查 robots.txt...")
        robots_url = f"{SITE_URL}/robots.txt"
        r = self.fetch_url(robots_url)
        if r and r.status_code == 200:
            print("    ✅ robots.txt: 可访问")
            if "Sitemap:" not in r.text:
                self.add_finding(
                    module="ia",
                    severity=SEVERITY_LOW,
                    title="robots.txt 未引用 sitemap",
                    description="robots.txt 中没有 Sitemap 指令",
                    location=robots_url,
                    recommendation="在 robots.txt 末尾添加 'Sitemap: https://www.chinaboundtravel.com/sitemap.xml'",
                    auto_fixable=True,
                )
                print("    ⚠️ robots.txt: 未引用 sitemap")
        else:
            self.add_finding(
                module="ia",
                severity=SEVERITY_MEDIUM,
                title="robots.txt 无法访问",
                description=f"robots.txt 返回状态码 {r.status_code if r else 'N/A'}",
                location=robots_url,
                recommendation="创建 robots.txt 文件",
                auto_fixable=True,
            )
            print("    ❌ robots.txt: 无法访问")

        # 6.4 检查 404 页面
        print("  📋 检查 404 页面...")
        r = self.fetch_url(f"{SITE_URL}/nonexistent-page-12345/")
        if r and r.status_code == 404:
            print("    ✅ 404 页面: 正常返回 404")
        elif r and r.status_code == 200:
            self.add_finding(
                module="ia",
                severity=SEVERITY_MEDIUM,
                title="404 页面返回 200 状态码",
                description="不存在的页面返回 200 状态码，应返回 404",
                location=f"{SITE_URL}/nonexistent-page-12345/",
                recommendation="配置正确的 404 页面和状态码",
                auto_fixable=True,
            )
            print("    ❌ 404 状态码: 错误（返回 200）")

        print(f"  📊 信息架构审计完成: {sum(1 for f in self.findings if f.module == 'ia')} 个发现")

    # ============================================================
    # 运行全部审计
    # ============================================================
    def run_all(self) -> Dict:
        """运行全部 6 个审计模块"""
        print("\n" + "=" * 60)
        print("  ChinaBound Travel - Site Health Audit Engine v1.0")
        print("=" * 60)
        print(f"  审计时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  目标网站: {SITE_URL}")
        print(f"  审计模块: 6 个")

        self.audit_security_config()
        self.audit_conversion_funnel()
        self.audit_technical_seo()
        self.audit_content_quality()
        self.audit_ux_design()
        self.audit_ia()

        # 生成报告
        return self.generate_report()

    def generate_report(self) -> Dict:
        """生成审计报告"""
        print("\n" + "=" * 60)
        print("  审计报告汇总")
        print("=" * 60)

        # 按模块和严重程度统计
        by_module = {}
        by_severity = {}
        for f in self.findings:
            by_module[f.module] = by_module.get(f.module, 0) + 1
            by_severity[f.severity] = by_severity.get(f.severity, 0) + 1

        print(f"\n  总发现数: {len(self.findings)}")
        print(f"\n  按严重程度:")
        for sev in [SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW, SEVERITY_INFO]:
            count = by_severity.get(sev, 0)
            if count > 0:
                print(f"    {sev:10s}: {count}")

        print(f"\n  按模块:")
        module_names = {
            "security": "安全/配置",
            "conversion": "转化漏斗",
            "seo": "技术SEO",
            "content": "内容质量",
            "ux": "UX/设计",
            "ia": "信息架构",
        }
        for mod, name in module_names.items():
            count = by_module.get(mod, 0)
            print(f"    {name:12s}: {count}")

        # 可自动修复的
        auto_fixable = [f for f in self.findings if f.auto_fixable]
        print(f"\n  可自动修复: {len(auto_fixable)} 项")
        print(f"  需人工处理: {len(self.findings) - len(auto_fixable)} 项")

        # 保存 JSON 报告
        report = {
            "audit_version": "1.0",
            "audit_time": datetime.now().isoformat(),
            "site_url": SITE_URL,
            "summary": {
                "total_findings": len(self.findings),
                "by_severity": by_severity,
                "by_module": by_module,
                "auto_fixable": len(auto_fixable),
                "manual_required": len(self.findings) - len(auto_fixable),
            },
            "findings": [f.to_dict() for f in self.findings],
        }

        json_path = REPORTS_DIR / "site_health_audit.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n  💾 JSON 报告: {json_path}")

        # 保存 Markdown 报告
        md_path = REPORTS_DIR / "site_health_audit.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# ChinaBound Travel - Site Health Audit Report\n\n")
            f.write(f"**审计时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**目标网站**: {SITE_URL}\n")
            f.write(f"**审计版本**: 1.0\n\n")
            f.write(f"## 总览\n\n")
            f.write(f"- **总发现数**: {len(self.findings)}\n")
            f.write(f"- **可自动修复**: {len(auto_fixable)}\n")
            f.write(f"- **需人工处理**: {len(self.findings) - len(auto_fixable)}\n\n")
            f.write(f"### 按严重程度\n\n")
            for sev in [SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW]:
                count = by_severity.get(sev, 0)
                if count > 0:
                    f.write(f"- **{sev}**: {count}\n")
            f.write(f"\n### 按模块\n\n")
            for mod, name in module_names.items():
                count = by_module.get(mod, 0)
                f.write(f"- **{name}**: {count}\n")
            f.write(f"\n## 详细发现\n\n")
            for sev in [SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW, SEVERITY_INFO]:
                sev_findings = [f for f in self.findings if f.severity == sev]
                if sev_findings:
                    f.write(f"### {sev}\n\n")
                    for i, finding in enumerate(sev_findings, 1):
                        f.write(f"**{i}. [{finding.module}] {finding.title}**\n\n")
                        f.write(f"- **描述**: {finding.description}\n")
                        if finding.location:
                            f.write(f"- **位置**: {finding.location}\n")
                        f.write(f"- **建议**: {finding.recommendation}\n")
                        f.write(f"- **可自动修复**: {'是' if finding.auto_fixable else '否'}\n\n")

        print(f"  💾 Markdown 报告: {md_path}")

        return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Site Health Audit Engine")
    parser.add_argument("--all", action="store_true", help="运行全部审计")
    parser.add_argument("--security", action="store_true", help="仅安全/配置审计")
    parser.add_argument("--conversion", action="store_true", help="仅转化漏斗审计")
    parser.add_argument("--seo", action="store_true", help="仅技术SEO审计")
    parser.add_argument("--content", action="store_true", help="仅内容质量审计")
    parser.add_argument("--ux", action="store_true", help="仅UX/设计审计")
    parser.add_argument("--ia", action="store_true", help="仅信息架构审计")
    args = parser.parse_args()

    auditor = SiteHealthAuditor()

    if args.all or not any([args.security, args.conversion, args.seo, args.content, args.ux, args.ia]):
        auditor.run_all()
    else:
        if args.security:
            auditor.audit_security_config()
        if args.conversion:
            auditor.audit_conversion_funnel()
        if args.seo:
            auditor.audit_technical_seo()
        if args.content:
            auditor.audit_content_quality()
        if args.ux:
            auditor.audit_ux_design()
        if args.ia:
            auditor.audit_ia()
        auditor.generate_report()


if __name__ == "__main__":
    main()
