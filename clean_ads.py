#!/usr/bin/env python3
import re

def clean_vpn_ads(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 找到所有VPN广告的位置
    vpn_pattern = r'> \*\*Stay Connected:\*\* Need reliable internet in China\? Get a VPN that works even in remote areas\.\s*\(#TP_VPN_PLACEHOLDER#\)\n\n\n'
    matches = list(re.finditer(vpn_pattern, content))
    
    print(f"找到 {len(matches)} 个VPN广告占位符")
    
    # 只保留前3个（开头、VPN章节开头、推荐部分）
    # 删除其余的广告
    
    # 从后往前删除，避免索引混乱
    keep_indices = [0, 3, 11]  # 保留特定位置的广告
    
    new_content = content
    deleted_count = 0
    
    # 找到所有匹配位置
    positions = []
    for i, match in enumerate(matches):
        positions.append((i, match.start(), match.end()))
    
    # 按结束位置倒序排列
    positions.sort(key=lambda x: x[2], reverse=True)
    
    for idx, start, end in positions:
        if idx not in keep_indices:
            new_content = new_content[:start] + new_content[end:]
            deleted_count += 1
    
    # 清理多余的空行
    new_content = re.sub(r'\n{4,}', '\n\n\n', new_content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"已删除 {deleted_count} 个VPN广告，保留 {len(keep_indices)} 个")
    return deleted_count

if __name__ == "__main__":
    file_path = "content/posts/internet-connection-china-esim-vpn-guide.md"
    clean_vpn_ads(file_path)
    print("清理完成！")