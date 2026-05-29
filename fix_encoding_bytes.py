import glob

def fix_file_encoding(filepath):
    with open(filepath, 'rb') as f:
        content_bytes = f.read()
    
    try:
        content = content_bytes.decode('utf-8')
    except:
        try:
            content = content_bytes.decode('gbk')
        except:
            content = content_bytes.decode('gb2312', errors='replace')
    
    garbled_patterns = [
        ('\u9910\u613f', ''),
        ('\u9280\u53c8', ''),
        ('\u949d\u203f', '→'),
        ('\u6f5c\u6839\u53e4', '外滩'),
        ('\u95e8\u5bb6\u5c0e', '陆家嘴'),
        ('\u7426\u4e0a\u56ed', 'Park'),
        ('\u9ec3\u6c99\u5317\u8def', 'Huangshang Road'),
        ('\u70e6\u5c0f\u9f8d\u5b9a', 'xiaolongbao'),
        ('\u6cd5\u79c1\u5229', 'French Concession'),
        ('\u6dee\u6c34\u4e2d\u8def', 'Huaihai Middle Road'),
        ('\u65b0\u5929\u5730', 'Xintiandi'),
        ('\u7530\u5b50\u65b9', 'Tianzifang'),
        ('\u6b66\u5eb7\u8def', 'Ferguson Lane'),
        ('\u660e\u661f\u9053', 'Yunnan Road'),
        ('\u5927\u4e16\u754c', 'Dashijie'),
        ('\u5eb7\u5e08\u82b1\u56ed', 'Kezhi Garden'),
        ('\u591a\u5c11\u91d1', 'how much'),
        ('\u4e0d\u8981\u8fa3', 'no spice'),
        ('\u8bdd\u8bdd', 'thanks'),
        ('\u9501\u5b9a\u5730', '90-year-old restaurant'),
        ('\u9910\u613f\u613f', ''),
        ('\u9280\u53c8\u53c8', ''),
        ('\u949d\u949d', '-'),
        ('\u95e8\u95e8', ''),
        ('\u6f5c\u6f5c', ''),
        ('\u7426\u7426', ''),
        ('\u9ec3\u9ec3', ''),
        ('\u70e6\u70e6', ''),
        ('\u6cd5\u6cd5', ''),
        ('\u6dee\u6dee', ''),
        ('\u65b0\u65b0', ''),
        ('\u7530\u7530', ''),
        ('\u6b66\u6b66', ''),
        ('\u660e\u660e', ''),
        ('\u5927\u5927', ''),
        ('\u5eb7\u5eb7', ''),
        ('\u591a\u591a', ''),
        ('\u4e0d\u4e0d', ''),
        ('\u8bdd\u8bdd', ''),
        ('\u9501\u9501', ''),
        ('\u9f8d\u9f8d', ''),
        ('\u5b9a\u5b9a', ''),
        ('\u53e4\u53e4', ''),
        ('\u5c0f\u5c0f', ''),
        ('\u9053\u9053', ''),
        ('\u8def\u8def', ''),
        ('\u56ed\u56ed', ''),
        ('\u8fa3\u8fa3', ''),
        ('\u5c11\u5c11', ''),
        ('\u4e2d\u4e2d', ''),
        ('\u4e2d\u8def', ''),
        ('\u6c34\u6c34', ''),
        ('\u6c34\u8def', ''),
        ('\u82b1\u82b1', ''),
        ('\u56ed\u82b1', ''),
    ]
    
    original_content = content
    for garbled, replacement in garbled_patterns:
        content = content.replace(garbled, replacement)
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"FIXED: {filepath}")
        return True
    return False

def main():
    md_files = glob.glob("content/**/*.md", recursive=True)
    fixed_count = 0
    
    for filepath in md_files:
        if fix_file_encoding(filepath):
            fixed_count += 1
    
    print(f"\n修复完成！共修复 {fixed_count} 个文件")

if __name__ == "__main__":
    main()
