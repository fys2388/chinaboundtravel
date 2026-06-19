import glob

def remove_non_ascii(filepath):
    with open(filepath, 'rb') as f:
        content = f.read()
    
    text = content.decode('utf-8', errors='replace')
    
    # 只保留ASCII字符和一些常用符号
    cleaned = ''
    for char in text:
        if ord(char) < 128 or char in '→':
            cleaned += char
    
    if cleaned != text:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(cleaned)
        print(f"Cleaned: {filepath}")
        return True
    return False

def main():
    md_files = glob.glob("content/**/*.md", recursive=True)
    cleaned_count = 0
    
    for filepath in md_files:
        if remove_non_ascii(filepath):
            cleaned_count += 1
    
    print(f"\nDone! Cleaned {cleaned_count} files")

if __name__ == "__main__":
    main()
