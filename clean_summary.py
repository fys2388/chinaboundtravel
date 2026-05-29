import os
import re

def clean_summary(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    pattern = r'(summary\s*=\s*["\'])([^"\']*?)(["\'])'
    def clean_match(match):
        original = match.group(2)
        cleaned = re.sub(r'>\s*\*\*[^\*]+\*\*.*?(https?://[^\s]+)?', '', original)
        cleaned = cleaned.strip()
        if len(cleaned) > 200:
            cleaned = cleaned[:200] + '...'
        return f"{match.group(1)}{cleaned}{match.group(3)}"
    
    new_content = re.sub(pattern, clean_match, content)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Cleaned:", os.path.basename(filepath))
    else:
        print("Already clean:", os.path.basename(filepath))

for filename in os.listdir('content/posts'):
    if filename.endswith('.md'):
        clean_summary(f'content/posts/{filename}')

print("\nSummary cleaning completed!")