import os
import re
from pathlib import Path

os.chdir(r'e:\AI\dulizhan\travel-blog')

# 需要修复的文章列表（有 ![xxx] 格式错误的）
files_to_fix = [
    "content/posts/2026-06-06-budget-planning-for-china-lessons-from-a-california-kid-turned-chengdu-local.md",
    "content/posts/2026-06-06-from-hollywood-to-hotpot-my-survival-guide-to-chinese-transportation-with-a-side-of-chaos.md",
    "content/posts/2026-06-06-the-best-time-to-visit-chengdu-a-decade-of-living-in-chinas-panda-capital.md",
    "content/posts/2026-06-06-the-sweet-spot-when-to-visit-chengdu-and-why-your-european-calendar-needs-a-reset.md",
    "content/posts/2026-06-06-the-tao-of-tummy-aches-a-chengdu-food-survival-guide-for-the-california-palate.md",
]

# 图片描述映射（根据文章主题生成合适的描述）
image_descriptions = {
    "budget-planning": [
        "[Image:Budget traveler counting Chinese yuan banknotes at street food stall in Chengdu, practical money management scene]",
        "[Image:Local market shopping scene with foreign tourist negotiating prices, authentic China travel experience]"
    ],
    "from-hollywood-to-hotpot": [
        "[Image:Chengdu subway station with crowds of commuters and neon signs, modern Chinese public transportation]",
        "[Image:Taxi ride through busy Chinese city streets at night, urban transportation experience]"
    ],
    "the-best-time-to-visit-chengdu": [
        "[Image:Giant pandas eating bamboo in Chengdu Research Base, spring morning with cherry blossoms]",
        "[Image:Chengdu cityscape with ancient temples and modern buildings, perfect travel season view]"
    ],
    "the-sweet-spot-when-to-visit-chengdu": [
        "[Image:Chengdu pandas in autumn forest with golden leaves, ideal visiting season scenery]",
        "[Image:Traditional tea house in Chengdu with locals enjoying afternoon tea, cultural experience]"
    ],
    "the-tao-of-tummy-aches": [
        "[Image:Sichuan hotpot bubbling with red chili oil and fresh ingredients, authentic Chengdu street food]",
        "[Image:Foreign traveler enjoying spicy noodles at night market, culinary adventure moment]"
    ]
}

def get_image_descriptions(filename):
    """根据文件名获取合适的图片描述"""
    for key, descs in image_descriptions.items():
        if key in filename:
            return descs
    # 默认描述
    return [
        "[Image:Chinese travel scene with tourists exploring ancient streets, cultural discovery moment]",
        "[Image:Authentic China travel experience with local interactions, memorable journey snapshot]"
    ]

def fix_article(filepath):
    """修复单篇文章"""
    path = Path(filepath)
    if not path.exists():
        print(f"  [SKIP] {path.name} - file not found")
        return False
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否有 ![xxx] 格式的图片
    md_images = re.findall(r'!\[[^\]]*\]\([^)]*\)', content)
    if not md_images:
        print(f"  [OK] {path.name} - no ![xxx] format images")
        return False
    
    print(f"  [FIX] {path.name} - found {len(md_images)} ![xxx] images")
    
    # 获取合适的图片描述
    descs = get_image_descriptions(filepath)
    
    # 删除所有 ![xxx] 格式的图片
    for img in md_images:
        content = content.replace(img, '')
    
    # 清理多余的空行
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # 找到导语后的位置（第一个 ## 标题之前或第一段之后）
    parts = content.split('---', 2)
    if len(parts) >= 3:
        frontmatter = parts[1]
        body = parts[2]
    else:
        frontmatter = ""
        body = content
    
    # 在正文开头插入第一个图片占位符
    body = body.strip()
    lines = body.split('\n')
    
    # 找到导语段落结束位置（第一个空行或 ## 标题）
    insert_pos_1 = 0
    for i, line in enumerate(lines):
        if line.startswith('##') or (line.strip() == '' and i > 0):
            insert_pos_1 = i
            break
    
    # 插入第一个图片占位符
    lines.insert(insert_pos_1, '')
    lines.insert(insert_pos_1 + 1, descs[0])
    
    # 找到正文中段位置（大约一半的位置，找一个合适的段落）
    mid_point = len(lines) // 2
    insert_pos_2 = mid_point
    for i in range(mid_point, min(mid_point + 10, len(lines))):
        if lines[i].strip() == '' or lines[i].startswith('##'):
            insert_pos_2 = i
            break
    
    # 插入第二个图片占位符
    lines.insert(insert_pos_2, '')
    lines.insert(insert_pos_2 + 1, descs[1])
    
    # 重新组合
    body = '\n'.join(lines)
    
    if frontmatter:
        content = f"---{frontmatter}---\n\n{body}"
    else:
        content = body
    
    # 保存
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"  [DONE] {path.name} - replaced with [Image:xxx] placeholders")
    return True

# 执行修复
print("=" * 60)
print("Batch fix: Convert ![xxx] to [Image:xxx] format")
print("=" * 60)

fixed_count = 0
for filepath in files_to_fix:
    if fix_article(filepath):
        fixed_count += 1

print()
print("=" * 60)
print(f"Fixed {fixed_count} articles")
print("=" * 60)
