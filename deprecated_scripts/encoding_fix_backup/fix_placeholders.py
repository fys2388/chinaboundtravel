#!/usr/bin/env python3
"""
占位符修复脚本
将 #TP_VPN_PLACEHOLDER# 和 #TP_BOOKING_PLACEHOLDER# 替换为真实的联盟链接
"""

import os
import re
from pathlib import Path

# 联盟链接配置
VPN_AFFILIATE_LINK = "https://www.expressvpn.com/offer/chinabound?offer=3monthsfree"
BOOKING_AFFILIATE_LINK = "https://www.booking.com/index.html?aid=YOUR_AFFILIATE_ID&label=chinabound"

def fix_placeholders(content_dir: str = "content"):
    """修复所有占位符"""
    content_path = Path(content_dir)
    
    vpn_placeholder = "#TP_VPN_PLACEHOLDER#"
    booking_placeholder = "#TP_BOOKING_PLACEHOLDER#"
    
    vpn_replacement = f"[Get ExpressVPN (3 months free)]({VPN_AFFILIATE_LINK})"
    booking_replacement = f"[Book on Booking.com]({BOOKING_AFFILIATE_LINK})"
    
    stats = {
        "vpn_count": 0,
        "booking_count": 0,
        "files_modified": 0
    }
    
    for md_file in content_path.rglob("*.md"):
        try:
            content = md_file.read_text(encoding='utf-8')
            original_content = content
            
            # 替换 VPN 占位符
            if vpn_placeholder in content:
                content = content.replace(vpn_placeholder, vpn_replacement)
                stats["vpn_count"] += content.count(vpn_replacement) - original_content.count(vpn_replacement)
            
            # 替换 Booking 占位符
            if booking_placeholder in content:
                content = content.replace(booking_placeholder, booking_replacement)
                stats["booking_count"] += content.count(booking_replacement) - original_content.count(booking_replacement)
            
            # 如果有修改，写回文件
            if content != original_content:
                md_file.write_text(content, encoding='utf-8')
                stats["files_modified"] += 1
                print(f"✅ Fixed: {md_file}")
        
        except Exception as e:
            print(f"❌ Error processing {md_file}: {e}")
    
    return stats

def main():
    print("=" * 60)
    print("占位符修复脚本")
    print("=" * 60)
    print()
    
    # 运行修复
    stats = fix_placeholders()
    
    print()
    print("=" * 60)
    print("修复统计:")
    print(f"  VPN 占位符替换: {stats['vpn_count']} 处")
    print(f"  Booking 占位符替换: {stats['booking_count']} 处")
    print(f"  修改文件数: {stats['files_modified']} 个")
    print("=" * 60)
    
    if stats["files_modified"] > 0:
        print()
        print("⚠️ 注意: 请在 Booking.com 联盟后台获取真实的 Affiliate ID")
        print("   并更新脚本中的 BOOKING_AFFILIATE_LINK 变量")
        print()
        print("✅ 修复完成！请运行 'git diff' 查看更改")

if __name__ == "__main__":
    main()
