import re

filepath = 'scripts/content_coverage_audit.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 找到 audit_image_formats 函数并替换
old_func = '''def audit_image_formats() -> Dict:
    """审计图片格式覆盖率"""
    if not IMG_DIR.exists():
        return {"total": 0, "webp": 0, "jpg": 0, "png": 0, "webp_rate": 0, "passed": False, "threshold": THRESHOLDS["webp_conversion"]}

    webp = list(IMG_DIR.rglob("*.webp"))
    jpg = list(IMG_DIR.rglob("*.jpg")) + list(IMG_DIR.rglob("*.jpeg"))
    png = list(IMG_DIR.rglob("*.png"))
    total = len(webp) + len(jpg) + len(png)
    webp_rate = round(len(webp) / total * 100, 1) if total else 0

    # 列出最大的 JPG 文件（优化候选）
    jpg_with_size = [(f.name, f.stat().st_size) for f in jpg]
    jpg_with_size.sort(key=lambda x: x[1], reverse=True)

    return {
        "total": total,
        "webp": len(webp),
        "jpg": len(jpg),
        "png": len(png),
        "webp_rate": webp_rate,
        "threshold": THRESHOLDS["webp_conversion"],
        "passed": webp_rate >= THRESHOLDS["webp_conversion"],
        "top_jpg_candidates": [{"name": n, "size_kb": round(s / 1024, 1)} for n, s in jpg_with_size[:10]],
    }'''

new_func = '''def audit_image_formats() -> Dict:
    """审计图片格式覆盖率"""
    if not IMG_DIR.exists():
        return {"total": 0, "webp": 0, "jpg": 0, "png": 0, "webp_rate": 0, "passed": False, "threshold": THRESHOLDS["webp_conversion"]}

    webp = list(IMG_DIR.rglob("*.webp"))
    jpg = list(IMG_DIR.rglob("*.jpg")) + list(IMG_DIR.rglob("*.jpeg"))
    png = list(IMG_DIR.rglob("*.png"))
    total = len(webp) + len(jpg) + len(png)

    # P1-FIX: WebP 转化率 = 有 WebP 版本的 JPG 比例（而非 WebP 数量占比）
    # 网站通常同时保留 JPG 和 WebP，用 <picture> 标签让浏览器选择
    jpg_with_webp = 0
    jpg_without_webp = []
    for j in jpg:
        w = j.with_suffix('.webp')
        if w.exists() and w.stat().st_size > 0:
            jpg_with_webp += 1
        else:
            jpg_without_webp.append(j)

    webp_rate = round(jpg_with_webp / len(jpg) * 100, 1) if jpg else 0

    # 列出最大的、没有 WebP 版本的 JPG 文件（优化候选）
    jpg_with_size = [(f.name, f.stat().st_size) for f in jpg_without_webp]
    jpg_with_size.sort(key=lambda x: x[1], reverse=True)

    return {
        "total": total,
        "webp": len(webp),
        "jpg": len(jpg),
        "png": len(png),
        "webp_rate": webp_rate,
        "jpg_with_webp": jpg_with_webp,
        "jpg_without_webp": len(jpg_without_webp),
        "threshold": THRESHOLDS["webp_conversion"],
        "passed": webp_rate >= THRESHOLDS["webp_conversion"],
        "top_jpg_candidates": [{"name": n, "size_kb": round(s / 1024, 1)} for n, s in jpg_with_size[:10]],
    }'''

if old_func in content:
    content = content.replace(old_func, new_func)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ 成功替换 audit_image_formats 函数")
else:
    print("❌ 未找到匹配的函数内容")
    # 打印函数附近的内容以便调试
    idx = content.find('def audit_image_formats')
    if idx >= 0:
        print("找到函数定义，位置:", idx)
        print("函数内容前500字符:")
        print(repr(content[idx:idx+500]))
