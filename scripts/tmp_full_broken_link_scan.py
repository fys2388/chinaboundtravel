# 临时脚本：全站断链扫描（内容 66 篇 + 站点页 13 个，基于 public/ 构建产物验证 URL 是否真实存在）
# 用法：先 hugo build，再运行本脚本。用完即删。
import re, pathlib, json

BASE = pathlib.Path(".")
PUBLIC = BASE / "public"

# 1) 收集所有已构建页面（含 .html 与目录型 index.html）
real_pages = set()
for f in PUBLIC.rglob("*.html"):
    rel = f.relative_to(PUBLIC).as_posix()
    if rel.endswith("index.html"):
        p = pathlib.PurePosixPath(rel).parent.as_posix()
        real_pages.add("/" + p if p != "." else "/")
    else:
        p = f.with_suffix("").relative_to(PUBLIC).as_posix()
        real_pages.add("/" + p)

def page_exists(path):
    # path 形如 /posts/xxx/ 或 /xxx 或 /xxx/
    p = path.rstrip("/")
    if p == "":
        return True
    if p in real_pages or p + ".html" in real_pages or p + "/" in real_pages:
        return True
    return False

# 2) 扫描源文件
SOURCE_DIRS = [
    BASE / "content" / "posts",
    BASE / "content",  # 根级站点页
]
LINK_RE = re.compile(r'\]\((/[^)\s]+?/?)\)')
ABS_LINK_RE = re.compile(r'\]\((https?://[^)\s]+?)\)')

# 静态资源前缀：图片/CSS/JS 不走页面路由，单独标记（不计入「页面断链」）
STATIC_PREFIXES = ("/img/", "/static/", "/css/", "/js/", "/css/", "/favicon")

broken_page = []     # 真正的页面断链（/posts/xxx、/resources/ 等）
broken_static = []   # 静态资源缺失（仅记录，不阻断）
total_checked = 0
for d in SOURCE_DIRS:
    if not d.exists():
        continue
    for f in d.glob("*.md"):
        if ".audit_backup" in str(f):
            continue
        txt = f.read_text(encoding="utf-8")
        for m in LINK_RE.finditer(txt):
            url = m.group(1)
            total_checked += 1
            target = url.rstrip("/")
            if target in ("", "/"):
                continue
            if target.startswith(STATIC_PREFIXES):
                # 静态资源：检查 static/ 目录是否有该文件
                exists = (BASE / "static" / target.lstrip("/")).exists() or (BASE / "public" / target.lstrip("/")).exists()
                if not exists:
                    broken_static.append((str(f.relative_to(BASE)), txt[:m.start()].count("\n") + 1, url))
                continue
            if not page_exists(target):
                line_no = txt[:m.start()].count("\n") + 1
                broken_page.append({"file": str(f.relative_to(BASE)), "line": line_no, "url": url, "snippet": m.group(0)[:120]})
        # 绝对 URL（同域）
        for m in ABS_LINK_RE.finditer(txt):
            url = m.group(1)
            if "chinaboundtravel.com" not in url:
                continue
            path_part = url.split("chinaboundtravel.com", 1)[1].split("?", 1)[0]
            total_checked += 1
            if path_part.startswith(STATIC_PREFIXES):
                continue
            if not page_exists(path_part):
                line_no = txt[:m.start()].count("\n") + 1
                broken_page.append({"file": str(f.relative_to(BASE)), "line": line_no, "url": url, "snippet": m.group(0)[:120]})

print(f"检查链接总数: {total_checked}")
print(f"页面断链总数: {len(broken_page)}")
print(f"静态资源缺失: {len(broken_static)}")
print()
# 按文件分组
by_file = {}
for b in broken_page:
    by_file.setdefault(b["file"], []).append(b)
for fname, items in sorted(by_file.items()):
    print(f"=== {fname} ({len(items)} 条) ===")
    for it in items:
        print(f"   L{it['line']}: {it['url']}")

