#!/usr/bin/env python3
"""
postbuild_h1_inject.py — 向 Hugo 重定向桩页注入隐藏 <h1> 标签

背景:
  Hugo v0.147.0 的 aliases 功能使用内部硬编码模板生成 meta-refresh
  重定向桩页（redirect stub），不加载用户提供的 layouts/redirect.html
  模板。这些桩页含 0 个 <h1> 标签，导致 h1_structure 审计违规。

用法（构建后手动执行，不自动运行）:
  python scripts/postbuild_h1_inject.py --dest public/quality-content

效果:
  在 public/quality-content/posts/**/*.html 中，对含 meta http-equiv=refresh
  且不含 <h1 的文件，在 </head> 前注入一个隐藏 <h1> 标签。

约束:
  - 仅修改 public/ 下的构建产物，不修改源文件
  - 不修改已含 <h1> 的正常页面
  - 不修改 ops-dashboard、static/、assets/ 等目录
"""

import argparse
import pathlib
import re
import sys

HIDDEN_H1 = '<h1 style="display:none">Redirecting...</h1>'


def is_redirect_stub(html: str) -> bool:
    """判断 HTML 是否为 meta-refresh 重定向桩页（不含 <h1>）"""
    has_refresh = bool(re.search(r'<meta[^>]*http-equiv\s*=\s*["\']?refresh', html, re.I))
    has_h1 = bool(re.search(r'<h1[\s>]', html, re.I))
    return has_refresh and not has_h1


def inject_h1(html: str) -> str:
    """在 </head> 前注入隐藏 <h1>"""
    return html.replace('</head>', HIDDEN_H1 + '</head>')


def main():
    parser = argparse.ArgumentParser(
        description='向 Hugo 重定向桩页注入隐藏 <h1> 标签'
    )
    parser.add_argument(
        '--dest',
        default='public/quality-content',
        help='构建产物目录（默认: public/quality-content）',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='仅报告，不修改文件',
    )
    args = parser.parse_args()

    dest = pathlib.Path(args.dest)
    if not dest.exists():
        print(f'Error: directory not found: {dest}', file=sys.stderr)
        sys.exit(1)

    # 仅扫描 posts/ 目录下的 index.html
    posts_dir = dest / 'posts'
    if not posts_dir.exists():
        print(f'Error: posts directory not found: {posts_dir}', file=sys.stderr)
        sys.exit(1)

    fixed = 0
    skipped = 0

    for index_file in sorted(posts_dir.rglob('index.html')):
        html = index_file.read_text(encoding='utf-8', errors='replace')

        if not is_redirect_stub(html):
            skipped += 1
            continue

        if args.dry_run:
            print(f'[DRY-RUN] would inject H1: {index_file.relative_to(dest)}')
            fixed += 1
            continue

        new_html = inject_h1(html)
        index_file.write_text(new_html, encoding='utf-8')
        fixed += 1
        print(f'[FIXED] {index_file.relative_to(dest)}')

    print(f'\nSummary: {fixed} redirect stubs fixed, {skipped} normal pages skipped')


if __name__ == '__main__':
    main()
