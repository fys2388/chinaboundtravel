"""pytest 全局夹具。

PYTHONIOENCODING
----------------
本仓库 184 个脚本里有 128 个没有 `sys.stdout.reconfigure(encoding="utf-8")`。
它们在 Windows 上（控制台代码页 GBK）打印 ✅/⚠️/中文时会 UnicodeEncodeError 崩溃。

后果比「输出乱码」严重得多：脚本崩溃 → 返回非零退出码 → 依赖退出码的 CI 硬门控
误判失败（或反过来，`|| echo` 兜底把失败吞成 0）。`audit_summary_md.py` 就是这样
被点名的——`--fail` 在全绿时仍因编码崩溃返回 1，门控形同虚设。

逐个给 128 个脚本补 reconfigure 不现实，所以在测试侧统一注入：
  1. 导出 PYTHONIOENCODING=utf-8，所有 subprocess 继承；
  2. reconfigure 本进程 stdout/stderr，pytest 自己的收集输出也不会崩。

CI（ubuntu runner）本来就是 UTF-8，本段是空操作，不影响线上。
"""
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
for p in (REPO_ROOT, REPO_ROOT / "scripts", REPO_ROOT / "chinaboundtravel_social_bot"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
