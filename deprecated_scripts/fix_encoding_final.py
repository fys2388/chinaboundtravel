"""
终极乱码修复脚本 - 处理GB2312编码错误
"""
import os
import glob
import codecs

def detect_and_fix_encoding(filepath):
    """检测并修复文件编码"""
    try:
        # 先尝试按GB2312读取
        with open(filepath, 'rb') as f:
            content_bytes = f.read()
        
        try:
            content = content_bytes.decode('utf-8')
        except:
            # 尝试GB2312
            try:
                content = content_bytes.decode('gb2312')
            except:
                # 尝试GBK
                try:
                    content = content_bytes.decode('gbk')
                except:
                    return False
        
        # 替换常见乱码
        garbled_map = {
            "馃憢": "👋",
            "鈫?": "→",
            "澶栨哗": "外滩",
            "闄嗗鍢?": "陆家嘴",
            "璞洯": "公园",
            "榛勫潯鍖楄矾": "黄山路",
            "鐓庡皬绗煎寘": "煎小笼",
            "娉曠鐣?": "法租界",
            "镒?": "-",
            "镒": "-",
            "馃": "",
            "憢": "",
            "镟": "",
            "镞": "",
            "镙": "",
            "镠": "",
            "镡": "",
            "镢": "",
            "镣": "",
            "镤": "",
            "镥": "",
            "镦": "",
            "镧": "",
            "镨": "",
            "镩": "",
            "镪": "",
            "镫": "",
            "镬": "",
            "镮": "",
            "镲": "",
            "镳": "",
            "镴": "",
            "镵": "",
            "長": "长",
            "镸": "",
            "镹": "",
            "镺": "",
            "镻": "",
            "镼": "",
            "镽": "",
            "镾": "",
            "锕": "",
            "锖": "",
            "锗": "",
            "锘": "",
            "锝": "",
            "锞": "",
            "锟": "",
            "锠": "",
            "锢": "",
            "锣": "",
            "锤": "",
            "锥": "",
            "锦": "",
            "锧": "",
            "锨": "",
            "锩": "",
            "锪": "",
            "锫": "",
            "锬": "",
            "锭": "",
            "键": "",
            "锯": "",
            "锰": "",
            "锱": "",
            "锲": "",
            "锴": "",
            "锶": "",
            "锼": "",
            "锽": "",
            "锾": "",
            "锿": "",
            "镃": "",
            "镄": "",
            "镅": "",
            "镆": "",
            "镈": "",
            "镋": "",
            "镌": "",
            "镍": "",
            "镎": "",
            "镏": "",
            "镕": "",
            "彊": "强",
            "锔": "",
            "搷": "",
            "寙": "",
            "惣": "",
            "徍": "",
            "棑": "",
            "攋": "",
            "鈥": "-",
        }
        
        original_content = content
        for garbled, replacement in garbled_map.items():
            content = content.replace(garbled, replacement)
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"FIXED: {filepath}")
            return True
        return False
    
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

def main():
    print("="*70)
    print("          终极乱码修复脚本")
    print("="*70)
    
    md_files = glob.glob("content/**/*.md", recursive=True)
    fixed_count = 0
    
    for filepath in md_files:
        if detect_and_fix_encoding(filepath):
            fixed_count += 1
    
    print(f"\n修复完成！共修复 {fixed_count} 个文件")
    print("="*70)

if __name__ == "__main__":
    main()
