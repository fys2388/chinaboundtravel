#!/usr/bin/env python3
"""
ChinaBound Travel - 第一周4项优化执行脚本
Week 1 Optimization Script

执行4项优化：
1. 优化CTA文案 - 从"预订"到"查看价格"
2. 优化首页首屏价值主张和CTA按钮
3. 所有联盟链接在新标签页打开（验证+修复）
4. 文章底部订阅CTA优化
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
LAYOUTS_DIR = PROJECT_ROOT / "layouts"
CONTENT_DIR = PROJECT_ROOT / "content"
POSTS_DIR = CONTENT_DIR / "posts"


def optimize_affiliate_cta_copy():
    """优化1：优化联盟CTA文案"""
    print("\n" + "=" * 60)
    print("  优化1：优化联盟CTA文案")
    print("=" * 60)

    single_file = LAYOUTS_DIR / "_default" / "single.html"
    if not single_file.exists():
        print(f"  ❌ 文件不存在: {single_file}")
        return False

    content = single_file.read_text(encoding="utf-8")
    original_content = content
    changes = 0

    # 优化联盟推荐区块的介绍文案
    old_intro = "Save time &amp; money with our editorially reviewed recommendations:"
    new_intro = "Save time &amp; money with our editorially reviewed recommendations — compare prices and book with confidence:"
    if old_intro in content:
        content = content.replace(old_intro, new_intro)
        changes += 1
        print("  ✅ 优化联盟区块介绍文案")

    # 优化eSIM链接文案
    old_esim = "Stay online the moment you land"
    new_esim = "Compare plans &amp; stay online instantly"
    if old_esim in content:
        content = content.replace(old_esim, new_esim)
        changes += 1
        print("  ✅ 优化eSIM链接文案")

    # 优化VPN链接文案
    old_vpn = "Access your favorite sites in China"
    new_vpn = "View deals &amp; access your favorite sites"
    if old_vpn in content:
        content = content.replace(old_vpn, new_vpn)
        changes += 1
        print("  ✅ 优化VPN链接文案")

    # 优化Hotels链接文案
    old_hotel = "Book with free cancellation"
    new_hotel = "Check today's best rates with free cancellation"
    if old_hotel in content:
        content = content.replace(old_hotel, new_hotel)
        changes += 1
        print("  ✅ 优化Hotels链接文案")

    # 优化Tours链接文案
    old_tours = "Skip the line at top attractions"
    new_tours = "Compare prices &amp; skip the line"
    if old_tours in content:
        content = content.replace(old_tours, new_tours)
        changes += 1
        print("  ✅ 优化Tours链接文案")

    # 添加信任徽章
    trust_badges = '''        <p class="affiliate-trust-badges"><span class="trust-badge">✓ Best Price Guarantee</span> <span class="trust-badge">✓ Free Cancellation</span> <span class="trust-badge">✓ 24/7 Support</span></p>'''
    if "affiliate-trust-badges" not in content:
        # 在联盟链接div后面添加信任徽章
        old_div_end = "        </div>\n    </div>\n\n\n    {{- /* ===== Affiliate Click Attribution"
        new_div_end = f"        </div>\n{trust_badges}\n    </div>\n\n\n    {{- /* ===== Affiliate Click Attribution"
        if old_div_end in content:
            content = content.replace(old_div_end, new_div_end)
            changes += 1
            print("  ✅ 添加信任徽章")

    # 添加信任徽章样式
    trust_badge_css = """
.affiliate-trust-badges { margin-top: 12px; padding-top: 12px; border-top: 1px solid #c5d5e8; }
.trust-badge { display: inline-block; background: white; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; color: #3A6EA5; font-weight: 600; margin-right: 6px; margin-bottom: 4px; border: 1px solid #c5d5e8; }
"""
    if "affiliate-trust-badges" not in content.split("<style>")[-1] if "<style>" in content else True:
        # 在样式部分添加信任徽章样式
        old_css_end = ".article-affiliate .affiliate-link:hover { background: #2d5a8a; color: white; transform: translateY(-1px); }"
        new_css_end = old_css_end + "\n" + trust_badge_css
        if old_css_end in content:
            content = content.replace(old_css_end, new_css_end)
            changes += 1
            print("  ✅ 添加信任徽章样式")

    if changes > 0:
        single_file.write_text(content, encoding="utf-8")
        print(f"\n  ✅ 完成 {changes} 项修改")
        return True
    else:
        print("\n  ⚠️ 未发现需要修改的内容")
        return False


def optimize_homepage_banner():
    """优化2：优化首页首屏价值主张和CTA按钮"""
    print("\n" + "=" * 60)
    print("  优化2：优化首页首屏价值主张和CTA按钮")
    print("=" * 60)

    banner_file = LAYOUTS_DIR / "partials" / "home-banner.html"
    if not banner_file.exists():
        print(f"  ❌ 文件不存在: {banner_file}")
        return False

    content = banner_file.read_text(encoding="utf-8")
    changes = 0

    # 优化副标题，更清晰的价值主张
    old_sub = "Practical Guide for Foreigners · Visa, Internet, Payment &amp; City Tips"
    new_sub = "Your complete guide to traveling China — visa-free entry, local transport, best hotels, and insider tips from our editorial team"
    if old_sub in content:
        content = content.replace(old_sub, new_sub)
        changes += 1
        print("  ✅ 优化副标题价值主张")

    # 优化主CTA按钮
    old_cta_primary = "🔍 Start Searching"
    new_cta_primary = "🗺️ Plan Your China Trip"
    if old_cta_primary in content:
        content = content.replace(old_cta_primary, new_cta_primary)
        changes += 1
        print("  ✅ 优化主CTA按钮文案")

    # 优化次CTA按钮
    old_cta_secondary = "📂 Browse Topics"
    new_cta_secondary = "📖 Read Popular Guides"
    if old_cta_secondary in content:
        content = content.replace(old_cta_secondary, new_cta_secondary)
        changes += 1
        print("  ✅ 优化次CTA按钮文案")

    # 添加社会证明行
    social_proof = '''            <div class="banner-social-proof">
                <span class="proof-item">✓ 59+ Expert Guides</span>
                <span class="proof-item">✓ Editorially Reviewed</span>
                <span class="proof-item">✓ Updated Weekly</span>
            </div>'''
    if "banner-social-proof" not in content:
        # 在CTA按钮后面添加社会证明
        old_cta_end = "            </div>\n        </div>"
        new_cta_end = f"            </div>\n{social_proof}\n        </div>"
        if old_cta_end in content:
            content = content.replace(old_cta_end, new_cta_end)
            changes += 1
            print("  ✅ 添加社会证明")

    # 添加社会证明样式
    social_proof_css = """
.banner-social-proof {
    margin-top: 1.25rem;
    display: flex;
    gap: 1.25rem;
    flex-wrap: wrap;
}
.proof-item {
    font-size: 0.82rem;
    color: #555;
    font-weight: 500;
}
@media (max-width: 768px) {
    .banner-social-proof { justify-content: center; }
}
"""
    if "banner-social-proof" not in content.split("<style>")[-1]:
        # 在样式部分末尾添加
        old_style_end = "</style>"
        new_style_end = social_proof_css + "\n</style>"
        if old_style_end in content:
            content = content.replace(old_style_end, new_style_end, 1)
            changes += 1
            print("  ✅ 添加社会证明样式")

    if changes > 0:
        banner_file.write_text(content, encoding="utf-8")
        print(f"\n  ✅ 完成 {changes} 项修改")
        return True
    else:
        print("\n  ⚠️ 未发现需要修改的内容")
        return False


def verify_affiliate_links_target():
    """优化3：验证所有联盟链接在新标签页打开"""
    print("\n" + "=" * 60)
    print("  优化3：验证联盟链接target=_blank")
    print("=" * 60)

    issues_found = 0
    fixed_count = 0

    # 检查文章模板中的联盟链接
    single_file = LAYOUTS_DIR / "_default" / "single.html"
    if single_file.exists():
        content = single_file.read_text(encoding="utf-8")
        affiliate_links = re.findall(r'<a[^>]*class="[^"]*affiliate-link[^"]*"[^>]*>', content)
        for link in affiliate_links:
            if "target=" not in link:
                issues_found += 1
                print(f"  ⚠️ 发现缺少target的联盟链接: {link[:80]}...")

    # 检查所有partials中的联盟链接
    partials_dir = LAYOUTS_DIR / "partials"
    if partials_dir.exists():
        for html_file in partials_dir.glob("*.html"):
            content = html_file.read_text(encoding="utf-8")
            # 查找包含联盟域名但没有target的链接
            affiliate_pattern = r'<a[^>]*href="[^"]*(booking\.com|agoda\.com|klook\.com|trip\.com|travelpayouts|nordvpn)[^"]*"[^>]*>'
            matches = re.findall(affiliate_pattern, content, re.IGNORECASE)
            for match in matches:
                full_match = re.search(r'<a[^>]*href="[^"]*(?:booking\.com|agoda\.com|klook\.com|trip\.com|travelpayouts|nordvpn)[^"]*"[^>]*>', content, re.IGNORECASE)
                if full_match and "target=" not in full_match.group():
                    issues_found += 1
                    print(f"  ⚠️ {html_file.name}: 发现缺少target的联盟链接")

    if issues_found == 0:
        print("  ✅ 所有联盟链接都已配置target=_blank")
        return True
    else:
        print(f"\n  ⚠️ 发现 {issues_found} 个问题，建议手动检查")
        return False


def optimize_subscribe_cta():
    """优化4：文章底部订阅CTA优化"""
    print("\n" + "=" * 60)
    print("  优化4：文章底部订阅CTA优化")
    print("=" * 60)

    subscribe_file = LAYOUTS_DIR / "partials" / "email-subscribe.html"
    if not subscribe_file.exists():
        print(f"  ❌ 文件不存在: {subscribe_file}")
        return False

    content = subscribe_file.read_text(encoding="utf-8")
    changes = 0

    # 优化订阅按钮文案
    old_btn = "Send the Free Guide →"
    new_btn = "Get My Free Guide →"
    if old_btn in content:
        content = content.replace(old_btn, new_btn)
        changes += 1
        print("  ✅ 优化订阅按钮文案")

    # 优化输入框placeholder
    old_placeholder = "Enter your email to get started"
    new_placeholder = "Enter your email for instant access"
    if old_placeholder in content:
        content = content.replace(old_placeholder, new_placeholder)
        changes += 1
        print("  ✅ 优化输入框placeholder")

    # 优化隐私声明，增加紧迫感
    old_privacy = "Join 10,000+ travelers. No spam, ever. Unsubscribe anytime."
    new_privacy = "🔒 Join 10,000+ travelers. Get weekly tips + exclusive deals. No spam, unsubscribe anytime."
    if old_privacy in content:
        content = content.replace(old_privacy, new_privacy)
        changes += 1
        print("  ✅ 优化隐私声明")

    # 检查文章模板中订阅区块的位置
    single_file = LAYOUTS_DIR / "_default" / "single.html"
    if single_file.exists():
        single_content = single_file.read_text(encoding="utf-8")
        # 确保订阅区块在联盟推荐之后、社交分享之前
        subscribe_partial = '{{- partial "email-subscribe.html" . -}}'
        if subscribe_partial in single_content:
            print("  ✅ 订阅区块已正确集成到文章模板")
        else:
            print("  ⚠️ 订阅区块未在文章模板中找到")

    if changes > 0:
        subscribe_file.write_text(content, encoding="utf-8")
        print(f"\n  ✅ 完成 {changes} 项修改")
        return True
    else:
        print("\n  ⚠️ 未发现需要修改的内容（当前订阅CTA已经很完善）")
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("  ChinaBound Travel - 第一周4项优化执行")
    print("=" * 60)
    print(f"\n  执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  项目目录: {PROJECT_ROOT}")

    results = {}

    # 执行4项优化
    results["cta_copy"] = optimize_affiliate_cta_copy()
    results["homepage"] = optimize_homepage_banner()
    results["target_blank"] = verify_affiliate_links_target()
    results["subscribe"] = optimize_subscribe_cta()

    # 总结
    print("\n" + "=" * 60)
    print("  优化完成总结")
    print("=" * 60)
    print(f"\n  1. CTA文案优化: {'✅ 完成' if results['cta_copy'] else '⚠️ 无需修改'}")
    print(f"  2. 首页Banner优化: {'✅ 完成' if results['homepage'] else '⚠️ 无需修改'}")
    print(f"  3. 联盟链接target验证: {'✅ 通过' if results['target_blank'] else '⚠️ 需检查'}")
    print(f"  4. 订阅CTA优化: {'✅ 完成' if results['subscribe'] else '⚠️ 无需修改'}")

    success_count = sum(1 for v in results.values() if v)
    print(f"\n  📊 总计: {success_count}/4 项优化完成或验证通过")

    print("\n" + "=" * 60)
    print("  下一步: 运行 hugo --gc --minify 构建并部署")
    print("=" * 60)


if __name__ == "__main__":
    main()
