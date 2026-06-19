import glob

def fix_newlines_proper(filepath):
    with open(filepath, 'rb') as f:
        content = f.read()
    
    # 修复各种异常换行符
    # 移除多余的 \r 字符
    content = content.replace(b'\r\r', b'\r')
    content = content.replace(b'\r\r', b'\r')
    
    # 确保所有换行都是 \r\n
    content = content.replace(b'\r\n', b'\n')  # 先统一为 LF
    content = content.replace(b'\r', b'\n')    # 剩余的 \r 也转为 LF
    content = content.replace(b'\n', b'\r\n')  # 转换为 CRLF
    
    with open(filepath, 'wb') as f:
        f.write(content)
    
    print(f"Fixed: {filepath}")

def main():
    md_files = glob.glob("content/**/*.md", recursive=True)
    
    for filepath in md_files:
        fix_newlines_proper(filepath)
    
    print(f"\nDone! Fixed {len(md_files)} files")

if __name__ == "__main__":
    main()
