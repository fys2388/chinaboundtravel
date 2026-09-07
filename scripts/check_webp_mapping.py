import os
from pathlib import Path

img_dirs = [Path('static/img'), Path('static/images')]

jpg_without_webp = []
webp_without_jpg = []
empty_webp = []

all_jpg = set()
all_webp = set()

for img_dir in img_dirs:
    if not img_dir.exists():
        continue
    
    for jpg in list(img_dir.rglob("*.jpg")) + list(img_dir.rglob("*.jpeg")):
        all_jpg.add(jpg)
        webp = jpg.with_suffix('.webp')
        if not webp.exists():
            jpg_without_webp.append((jpg, webp, '不存在'))
        elif webp.stat().st_size == 0:
            jpg_without_webp.append((jpg, webp, '空文件'))
            empty_webp.append(webp)
    
    for webp in img_dir.rglob("*.webp"):
        all_webp.add(webp)
        # 检查是否有对应的 JPG
        jpg1 = webp.with_suffix('.jpg')
        jpg2 = webp.with_suffix('.jpeg')
        if not jpg1.exists() and not jpg2.exists():
            webp_without_jpg.append(webp)

print(f"总 JPG: {len(all_jpg)}")
print(f"总 WebP: {len(all_webp)}")
print(f"JPG 无对应 WebP: {len(jpg_without_webp)}")
print(f"WebP 无对应 JPG: {len(webp_without_jpg)}")
print(f"空 WebP 文件: {len(empty_webp)}")

if jpg_without_webp:
    print("\n=== JPG 无对应 WebP 的文件（前20个）===")
    for jpg, webp, reason in jpg_without_webp[:20]:
        print(f"  {jpg.name} ({jpg.stat().st_size // 1024} KB) -> {reason}")

if empty_webp:
    print("\n=== 空 WebP 文件（前10个）===")
    for webp in empty_webp[:10]:
        print(f"  {webp}")

# 检查是否有子目录
print("\n=== 目录结构 ===")
for img_dir in img_dirs:
    if img_dir.exists():
        print(f"\n{img_dir}:")
        for root, dirs, files in os.walk(img_dir):
            level = root.replace(str(img_dir), '').count(os.sep)
            indent = '  ' * level
            print(f"{indent}{os.path.basename(root)}/ ({len([f for f in files if f.endswith(('.jpg','.webp'))])} 张图片)")
