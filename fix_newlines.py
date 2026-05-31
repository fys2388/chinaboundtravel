import glob

def fix_newlines(filepath):
    with open(filepath, 'rb') as f:
        content = f.read()
    
    # 统一转换为 Windows 换行符
    content = content.replace(b'\r\n', b'\n')  # 先统一为 LF
    content = content.replace(b'\n', b'\r\n')  # 再转换为 CRLF
    
    with open(filepath, 'wb') as f:
        f.write(content)
    
    print(f"Fixed: {filepath}")

def main():
    md_files = glob.glob("content/**/*.md", recursive=True)
    
    for filepath in md_files:
        fix_newlines(filepath)
    
    print(f"\nDone! Fixed {len(md_files)} files")

if __name__ == "__main__":
    main()
