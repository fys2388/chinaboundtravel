# 临时脚本：删除 7 篇文章正文中的空括号（() （） ( )），不填任何中文
# 规则：只删空括号本身；如果空括号前面紧跟英文词（如 "Mapo Tofu ()"），删掉整个 " ()"
# 保留已有中文的括号（如 "Mapo Tofu (麻婆豆腐)"）—— 正则只匹配空括号
import re, pathlib, sys

TARGETS = [
    "content/posts/2026-07-06-a-gastronomic-adventure-in-china-a-foodies-guide-for-european-travelers.md",
    "content/posts/2026-07-05-yunnan-adventure-rice-terraces-ancient-towns-and-ethnic-minorities-guide.md",
    "content/posts/2026-07-03-guilin-and-yangshuo-the-ultimate-karst-landscape-guide-for-2026-guide.md",
    "content/posts/2026-05-27-how-to-survive-chinese-train-station.md",
    "content/posts/2026-06-30-zhangjiajie-avatar-mountains-complete-guide-to-chinas-most-spectacular-park.md",
    "content/posts/2026-05-26-hangzhou-west-lake-tea-culture-g20-guide.md",
    "content/posts/2026-08-12-china-national-parks-zhangjiajie-jiuzhaigou-and-beyond-guide.md",
]

# 匹配空括号：() （） ( ) （  ）
patterns = [
    (re.compile(r'\s+\(\)'), lambda m: ''),          # "text ()" -> "text"
    (re.compile(r'\s+（\s*）'), lambda m: ''),        # "text （）" -> "text"
    (re.compile(r'\(\s+\)'), lambda m: ''),           # "text ( )" -> "text"（中间有空格）
]
# 还有 "（  ）" 全角带空格
patterns.append((re.compile(r'（\s+）'), lambda m: ''))

total = 0
for fp in TARGETS:
    p = pathlib.Path(fp)
    if not p.exists():
        print(f"  跳过（不存在）: {fp}")
        continue
    txt = p.read_text(encoding="utf-8")
    changed = 0
    for pat, rep in patterns:
        txt, n = pat.subn(rep, txt)
        changed += n
    # 校验：不应再有空括号残留
    remaining = len(re.findall(r'\(\s*\)|（\s*）', txt))
    p.write_text(txt, encoding="utf-8")
    total += changed
    print(f"  删除 {changed} 处 | 残留 {remaining} 处 | {p.name}")
    assert remaining == 0, f"残留空括号: {remaining}"

print(f"\n共删除 {total} 处空括号，残留 0")
