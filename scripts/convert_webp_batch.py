import os
from pathlib import Path
from PIL import Image

def convert_jpg_to_webp(img_dir, quality=82):
    """批量转换 JPG 为 WebP"""
    jpg_files = list(img_dir.rglob("*.jpg")) + list(img_dir.rglob("*.jpeg"))
    
    converted = 0
    skipped = 0
    failed = 0
    total_saved = 0
    
    for jpg_path in jpg_files:
        webp_path = jpg_path.with_suffix('.webp')
        
        if webp_path.exists():
            skipped += 1
            continue
        
        try:
            img = Image.open(jpg_path)
            # 处理 RGBA 模式
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            original_size = jpg_path.stat().st_size
            img.save(webp_path, 'WEBP', quality=quality, method=6)
            new_size = webp_path.stat().st_size
            saved = original_size - new_size
            total_saved += saved
            
            converted += 1
            if converted % 20 == 0:
                print(f"  已转换 {converted} 张...")
                
        except Exception as e:
            failed += 1
            print(f"  ❌ 转换失败: {jpg_path.name} - {str(e)[:50]}")
    
    return converted, skipped, failed, total_saved

# 转换两个图片目录
img_dirs = [
    Path('static/img'),
    Path('static/images'),
]

total_converted = 0
total_skipped = 0
total_failed = 0
total_saved_all = 0

for img_dir in img_dirs:
    if not img_dir.exists():
        print(f"⏭️  目录不存在: {img_dir}")
        continue
    
    print(f"\n📁 处理目录: {img_dir}")
    converted, skipped, failed, saved = convert_jpg_to_webp(img_dir)
    total_converted += converted
    total_skipped += skipped
    total_failed += failed
    total_saved_all += saved
    print(f"  转换: {converted}, 已存在: {skipped}, 失败: {failed}")
    print(f"  节省空间: {saved / 1024:.1f} KB")

# 统计最终结果
print("\n" + "="*50)
print("📊 WebP 转换完成")
print("="*50)
print(f"  新转换: {total_converted} 张")
print(f"  已存在: {total_skipped} 张")
print(f"  失败: {total_failed} 张")
print(f"  总节省空间: {total_saved_all / 1024 / 1024:.2f} MB")

# 计算最终转化率
all_webp = 0
all_jpg = 0
for img_dir in img_dirs:
    if img_dir.exists():
        all_webp += len(list(img_dir.rglob("*.webp")))
        all_jpg += len(list(img_dir.rglob("*.jpg"))) + len(list(img_dir.rglob("*.jpeg")))

total = all_webp + all_jpg
rate = all_webp / total * 100 if total > 0 else 0
print(f"\n  最终统计: WebP={all_webp}, JPG={all_jpg}, 总计={total}")
print(f"  WebP 转化率: {rate:.1f}% (目标 80%)")
