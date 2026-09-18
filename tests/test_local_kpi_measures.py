"""测试 3 个新接线的本地 KPI 测量函数。

背景：这 3 个 KPI 的 source 声明分别是 social_image_validator /
cookie-consent审计 / content-quality-audit+api_health，前两个在仓库里
根本不存在，第三个依赖的脚本存在但门控有效性从未被验证。
27 个 no_data KPI 里的典型「声明了源、从没接上」。
"""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent

import sys

sys.path.insert(0, str(ROOT / "scripts"))

import agent_kpi_auditor as aud  # noqa: E402


def _img(p: Path, data: bytes = b"fakebytes"):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


# ============================================================
# _content_originality
# ============================================================

def test_originality_all_unique(tmp_path):
    r = tmp_path / "root"
    _img(r / "static/img/a.png", b"\x89PNG-A")
    _img(r / "static/img/b.png", b"\x89PNG-B")
    posts = r / "content" / "posts"
    posts.mkdir(parents=True)
    posts.joinpath("p1.md").write_text(
        "---\ntitle: A\n---\n" + ("Body one. " * 60), encoding="utf-8")
    posts.joinpath("p2.md").write_text(
        "---\ntitle: B\n---\n" + ("Body two. " * 60), encoding="utf-8")

    out = aud._content_originality(r)
    assert out["image_total"] == 2
    assert out["image_dups"] == 0
    assert out["post_total"] == 2
    assert out["post_dups"] == 0
    assert out["rate"] == 100.0


def test_originality_detects_duplicate_images(tmp_path):
    r = tmp_path / "root"
    _img(r / "static/img/orig.png", b"IMAGE-X")
    _img(r / "static/img/copy.png", b"IMAGE-X")
    _img(r / "static/img/unique.png", b"IMAGE-Y")

    out = aud._content_originality(r)
    assert out["image_total"] == 3
    assert out["image_dups"] == 1  # 3 个文件、2 种内容
    assert out["rate"] == pytest.approx(66.7, abs=0.1)


def test_originality_duplicate_body_ignores_frontmatter(tmp_path):
    """两篇文章只有 front-matter 不同 = 同一篇，必须算重复。"""
    r = tmp_path / "root"
    posts = r / "content" / "posts"
    posts.mkdir(parents=True)
    body = "Same body content here. " * 60
    posts.joinpath("a.md").write_text(
        "---\ntitle: Alpha\ndate: 2026-01-01\n---\n" + body, encoding="utf-8")
    posts.joinpath("b.md").write_text(
        "---\ntitle: Beta\ndate: 2026-02-01\n---\n" + body, encoding="utf-8")

    out = aud._content_originality(r)
    assert out["post_total"] == 2
    assert out["post_dups"] == 1
    assert out["rate"] < 100


def test_originality_skips_short_bodies(tmp_path):
    """太短的不判重（模板/占位页），否则会误报。"""
    r = tmp_path / "root"
    posts = r / "content" / "posts"
    posts.mkdir(parents=True)
    short = "Short." * 20  # ~120 chars，低于 200 阈值
    posts.joinpath("a.md").write_text("---\ntitle: A\n---\n" + short, encoding="utf-8")
    posts.joinpath("b.md").write_text("---\ntitle: B\n---\n" + short, encoding="utf-8")

    out = aud._content_originality(r)
    assert out["post_total"] == 0
    assert out["post_dups"] == 0
    # total=0 → 无法判定，而不是给一个虚假的 100 分
    assert out["rate"] is None
    assert out["note"]


def test_originality_empty_returns_note(tmp_path):
    r = tmp_path / "root"
    out = aud._content_originality(r)
    assert out["rate"] is None
    assert out["note"]


def test_originality_ignores_non_image_extensions(tmp_path):
    r = tmp_path / "root"
    (r / "static/img").mkdir(parents=True)
    (r / "static/img/readme.txt").write_bytes(b"not an image")
    (r / "static/img/data.json").write_bytes(b"{}")
    out = aud._content_originality(r)
    assert out["image_total"] == 0


# ============================================================
# _gdpr_compliance
# ============================================================

FULL_PRIVACY = (
    "---\ntitle: Privacy\n---\n\n"
    "You may access, delete, or rectify your personal data (Art.15-22).\n"
    "Unsubscribe from marketing emails at any time via the link in our footer.\n"
    "Cross-border transfer is governed by the EU-U.S. Data Privacy Framework and SCCs.\n"
)

BARE_PRIVACY = "---\ntitle: Privacy\n---\n\nJust a greeting. Thanks for visiting.\n"


def test_gdpr_full_compliance(tmp_path):
    r = tmp_path / "root"
    (r / "content").mkdir(parents=True)
    (r / "content/privacy-policy.md").write_text(FULL_PRIVACY, encoding="utf-8")
    (r / "content/terms-of-service.md").write_text("Terms.\n", encoding="utf-8")
    (r / "content/refund-policy.md").write_text("Refunds.\n", encoding="utf-8")
    (r / "functions/api").mkdir(parents=True)
    (r / "functions/api/subscribe.js").write_text(
        "export async function handler(req) { if (req.action === 'unsubscribe') {...} }\n",
        encoding="utf-8")
    (r / "layouts/partials").mkdir(parents=True)
    (r / "layouts/partials/pricing-table.html").write_text(
        '<input type="checkbox" required> I expressly authorize...', encoding="utf-8")

    out = aud._gdpr_compliance(r)
    assert out["total"] == 8
    assert out["passed"] == 8
    assert out["rate"] == 100.0


def test_gdpr_missing_privacy_policy_fails_multiple_items(tmp_path):
    """缺隐私政策页应同时拉低「存在」+「权利」+「退订」+「国际传输」4 项。"""
    r = tmp_path / "root"
    (r / "content").mkdir(parents=True)
    (r / "content/terms-of-service.md").write_text("Terms.\n", encoding="utf-8")
    (r / "content/refund-policy.md").write_text("Refunds.\n", encoding="utf-8")
    (r / "functions/api").mkdir(parents=True)
    (r / "functions/api/subscribe.js").write_text("unsubscribe", encoding="utf-8")
    (r / "layouts/partials").mkdir(parents=True)
    (r / "layouts/partials/pricing-table.html").write_text(
        "I expressly authorize", encoding="utf-8")

    out = aud._gdpr_compliance(r)
    failed = [c["name"] for c in out["checks"] if not c["passed"]]
    assert out["passed"] == 4  # 只有 terms/refund/subscribe/pricing 4 项
    assert out["total"] == 8
    assert out["rate"] == 50.0
    assert "隐私政策页存在" in failed


def test_gdpr_privacy_without_unsubscribe_fails_that_item(tmp_path):
    """有隐私政策页但没有退订机制——这是 GDPR Art.21 的硬缺。"""
    r = tmp_path / "root"
    (r / "content").mkdir(parents=True)
    (r / "content/privacy-policy.md").write_text(
        FULL_PRIVACY.replace("Unsubscribe from marketing emails at any time",
                             "We keep your data"),
        encoding="utf-8")
    (r / "content/terms-of-service.md").write_text("Terms.\n", encoding="utf-8")
    (r / "content/refund-policy.md").write_text("Refunds.\n", encoding="utf-8")
    (r / "functions/api").mkdir(parents=True)
    (r / "functions/api/subscribe.js").write_text("unsubscribe", encoding="utf-8")
    (r / "layouts/partials").mkdir(parents=True)
    (r / "layouts/partials/pricing-table.html").write_text(
        "I expressly authorize", encoding="utf-8")

    out = aud._gdpr_compliance(r)
    failed = [c["name"] for c in out["checks"] if not c["passed"]]
    assert "隐私政策含退订机制" in failed
    assert out["passed"] == 7


def test_gdpr_unsubscribe_endpoint_case_insensitive(tmp_path):
    """大小写不敏感：UNSUBSCRIBE 也应算通过。"""
    r = tmp_path / "root"
    (r / "functions/api").mkdir(parents=True)
    (r / "functions/api/subscribe.js").write_text(
        "action === 'UNSUBSCRIBE'", encoding="utf-8")
    out = aud._gdpr_compliance(r)
    sub = [c for c in out["checks"] if "订阅端点" in c["name"]][0]
    assert sub["passed"] is True


# ============================================================
# _ci_block_rate
# ============================================================

def _wf(r: Path, name: str, body: str):
    d = r / ".github" / "workflows"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(body, encoding="utf-8")


def test_ci_block_rate_all_wired(tmp_path):
    r = tmp_path / "root"
    (r / "scripts").mkdir(parents=True)
    (r / "scripts/content_id_audit.py").write_text("# ok\n", encoding="utf-8")
    (r / "scripts/cover_gate.py").write_text("# ok\n", encoding="utf-8")
    _wf(r, "deploy.yml", """
on: push
jobs:
  deploy:
    steps:
      - name: id gate
        run: python scripts/content_id_audit.py audit --strict
      - name: cover gate
        run: python scripts/cover_gate.py --strict
""")

    out = aud._ci_block_rate(r)
    assert out["gates"] == 2
    assert out["wired"] == 2
    assert out["rate"] == 100.0
    assert out["broken"] == []


def test_ci_block_rate_detects_missing_script(tmp_path):
    """门控引用不存在的脚本 = 门控形同虚设，P0 能直接流进生产。"""
    r = tmp_path / "root"
    (r / "scripts").mkdir(parents=True)
    (r / "scripts/real.py").write_text("# ok\n", encoding="utf-8")
    _wf(r, "deploy.yml", """
jobs:
  build:
    steps:
      - name: works
        run: python scripts/real.py --strict
      - name: broken
        run: python scripts/ghost.py --strict
""")

    out = aud._ci_block_rate(r)
    assert out["gates"] == 2
    assert out["wired"] == 1
    assert out["rate"] == 50.0
    assert len(out["broken"]) == 1
    assert out["broken"][0]["missing"] == ["scripts/ghost.py"]


def test_ci_block_rate_step_without_hard_fail_is_not_a_gate(tmp_path):
    """没有 exit 1 / --strict 的 step 不算门控——普通脚本调用不是阻断点。"""
    r = tmp_path / "root"
    (r / "scripts").mkdir(parents=True)
    (r / "scripts/report.py").write_text("# ok\n", encoding="utf-8")
    _wf(r, "report.yml", """
jobs:
  report:
    steps:
      - name: generate report
        run: python scripts/report.py
""")

    out = aud._ci_block_rate(r)
    assert out["gates"] == 0
    assert out["rate"] is None
    assert out["note"]


def test_ci_block_rate_or_pipe_hard_fail(tmp_path):
    """`|| exit 1` 是常见的硬失败写法，必须识别。"""
    r = tmp_path / "root"
    (r / "scripts").mkdir(parents=True)
    (r / "scripts/validator.py").write_text("# ok\n", encoding="utf-8")
    _wf(r, "w.yml", """
jobs:
  c:
    steps:
      - name: validate
        run: python scripts/validator.py || exit 1
""")

    out = aud._ci_block_rate(r)
    assert out["gates"] == 1
    assert out["rate"] == 100.0


def test_ci_block_rate_on_real_repo_is_fully_wired():
    """真实仓库：门控引用的脚本必须都存在。
    这是 2026-09-18 的接线基线——generator 静默失败的那类缺陷，
    在 CI 侧的对偶就是门控引用了不存在的脚本。"""
    out = aud._ci_block_rate(ROOT)
    assert out["gates"] >= 1, "仓库里应该至少有 1 个硬门控"
    assert out["broken"] == [], f"存在失效门控: {out['broken']}"
    assert out["rate"] == 100.0


# ============================================================
# 接线归属：三个新接的 KPI 必须接在正确的 Agent 下
# ============================================================

def test_new_kpis_land_on_the_right_agents():
    """KPI 定义和接线代码必须一致。

    content_originality 定义在 AGENTS['social'] 下，不
    是 content。接错 agent 的静默后果：collect_metrics 把值写进
    content，评分时 content 的 KPI 列表里没有这个 id，值被静默丢掉，
    KPI 永远显示「无数据」，覆盖率也不涨——没有任何报错。
    """
    ownership = {
        "content_originality": "social",
        "gdpr_compliance": "user",
        "ci_block_rate": "ops",
    }
    for kpi_id, agent_id in ownership.items():
        ids = [k["id"] for k in aud.AGENTS[agent_id]["kpis"]]
        assert kpi_id in ids, f"{kpi_id} 应该定义在 {agent_id} 下，实际缺失"

    metrics = aud.collect_metrics()
    for kpi_id, agent_id in ownership.items():
        assert metrics.get(agent_id, {}).get(kpi_id) is not None, (
            f"{agent_id}.{kpi_id} 未被接线（collect_metrics 没写入真实值）"
        )

