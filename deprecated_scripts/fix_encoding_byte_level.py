import glob

def fix_file_byte_level(filepath):
    with open(filepath, 'rb') as f:
        content_bytes = f.read()
    
    garbled_byte_patterns = [
        (b'\xe9\x94\x91\xe6\x83\xa1', b''),      # 馃憢
        (b'\xe9\x92\xa2\xe2\x80\x9f', b' -> '),   # 鈫?
        (b'\xe6\xb6\xa8\xe6\x9d\xa1\xe5\x93\x8d', b' (Bund)'),
        (b'\xe9\x97\xa8\xe5\xae\xb6\xe5\x89\x8d', b' (Lujiazui)'),
        (b'\xe7\x42\xe4\xb8\xad', b' (Park)'),
        (b'\xe6\xa3\xa0\xe6\xb6\x81\xe5\x8c\x97\xe8\xb7\xaf', b' (Huangshang Road)'),
        (b'\xe9\x85\xb8\xe5\xb0\x8f\xe9\xb9\xa4\xe5\xae\x9a', b'xiaolongbao'),
        (b'\xe5\xae\x9a\xe6\xb3\x95\u4e16\u754c', b' (French Concession)'),
        (b'\xe5\xa9\xa4\xe6\xb0\xb4\u4e2d\u8def', b' (Huaihai Middle Road)'),
        (b'\u65b0\u5929\u5730', b' (Xintiandi)'),
        (b'\u7530\u5b50\u65b9', b' (Tianzifang)'),
        (b'\u6b66\u5eb7\u8def', b' (Ferguson Lane)'),
        (b'\u660e\u661f\u9053', b' (Yunnan Road)'),
        (b'\u5927\u4e16\u754c', b' (Dashijie)'),
        (b'\u5eb7\u5e08\u82b1\u56ed', b' (Kezhi Garden)'),
        (b'\u591a\u5c11\u91d1', b' (how much)'),
        (b'\u4e0d\u8981\u8fa3', b' (no spice)'),
        (b'\u8bdd\u8bdd', b' (thanks)'),
        (b'\xe5\xae\x89', b''),
        (b'\xe5\xae\xb9', b''),
        (b'\xe5\xae\xa4', b''),
        (b'\xe5\xae\x9a', b''),
        (b'\xe5\xae\xa1', b''),
        (b'\xe5\xae\xb6', b''),
        (b'\xe5\xae\xbf', b''),
        (b'\xe5\xae\x9e', b''),
        (b'\xe5\xae\x8c', b''),
        (b'\xe9\x94', b''),
        (b'\xe6\x83', b''),
        (b'\xe2\x80\x9f', b''),
        (b'\xe6\xb6', b''),
        (b'\xe6\x9d', b''),
        (b'\xe5\x93', b''),
        (b'\xe9\x97', b''),
        (b'\xe5\x89', b''),
        (b'\xe7', b''),
        (b'\xe4\xb8', b''),
        (b'\xe6\xa3', b''),
        (b'\xe8\xb7', b''),
        (b'\xe9\x85', b''),
        (b'\xe5\xb0', b''),
        (b'\xe9\xb9', b''),
        (b'\xe6\xb3', b''),
        (b'\xe5\xa9', b''),
        (b'\xe6\xb0', b''),
        (b'\u4e16', b''),
        (b'\u754c', b''),
        (b'\u5929', b''),
        (b'\u5730', b''),
        (b'\u7530', b''),
        (b'\u5b50', b''),
        (b'\u6b66', b''),
        (b'\u5eb7', b''),
        (b'\u660e', b''),
        (b'\u661f', b''),
        (b'\u9053', b''),
        (b'\u5927', b''),
        (b'\u4e16', b''),
        (b'\u5e08', b''),
        (b'\u82b1', b''),
        (b'\u56ed', b''),
        (b'\u591a', b''),
        (b'\u5c11', b''),
        (b'\u91d1', b''),
        (b'\u4e0d', b''),
        (b'\u8981', b''),
        (b'\u8fa3', b''),
        (b'\u8bdd', b''),
        (b'\xe5\xae', b''),
        (b'\xe9\x94\x91', b''),
        (b'\xe6\x83\xa1', b''),
        (b'\xe9\x92\xa2', b''),
        (b'\xe6\xb6\xa8', b''),
        (b'\xe6\x9d\xa1', b''),
        (b'\xe5\x93\x8d', b''),
        (b'\xe9\x97\xa8', b''),
        (b'\xe5\x89\x8d', b''),
        (b'\xe7\x42', b''),
        (b'\xe6\xa3\xa0', b''),
        (b'\xe6\xb6\x81', b''),
        (b'\xe5\x8c\x97', b''),
        (b'\xe9\x85\xb8', b''),
        (b'\xe9\xb9\xa4', b''),
        (b'\xe5\xa9\xa4', b''),
    ]
    
    original_length = len(content_bytes)
    for pattern, replacement in garbled_byte_patterns:
        content_bytes = content_bytes.replace(pattern, replacement)
    
    if len(content_bytes) != original_length:
        with open(filepath, 'wb') as f:
            f.write(content_bytes)
        print(f"Fixed: {filepath} (removed {original_length - len(content_bytes)} bytes)")
        return True
    return False

def main():
    md_files = glob.glob("content/**/*.md", recursive=True)
    fixed_count = 0
    
    for filepath in md_files:
        if fix_file_byte_level(filepath):
            fixed_count += 1
    
    print(f"\nDone! Fixed {fixed_count} files")

if __name__ == "__main__":
    main()
