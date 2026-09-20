"""P0-FIX (2026-09-20): /api/subscribe 静默转化失败契约测试。

实测发现（2026-09-20，线上）：
    POST /api/subscribe {"email":"probe@example.com", ...}
    -> HTTP 200 {"success":true, "delivered_pdf":false,
                  "subscriber_created":true,
                  "detail":"Resend:422:...Invalid `to` field..."}

后端在 MailerLite/Resend 失败时仍返回 success:true，而两个前端表单只看
`resp.ok && data.success` 就显示「✅ Check your inbox — your guide is on its way!」。
客户被给了一个假承诺：以为订阅成功、指南在路，实际什么都没收到。
这是「报表表达状态但不表达真相」在转化路径上的同一类病。

这些测试是静态契约检查（不联网）：锁定 success 语义与前端分支，
防止将来有人再把 success 硬编码成 true。
"""
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SUBSCRIBE = REPO / "functions" / "api" / "subscribe.js"
FORMS = [
    REPO / "layouts" / "partials" / "email-subscribe.html",
    REPO / "layouts" / "shortcodes" / "lead-magnet-cta.html",
]


def _read(p):
    return p.read_text(encoding="utf-8")


class TestSubscribeBackendContract:
    def test_no_unconditional_success_true(self):
        """不得出现「result 初始化即 success:true」或「无条件置 true」的写法。"""
        src = _read(SUBSCRIBE)
        assert "success: true," not in src, (
            "subscribe.js 仍把 result.success 初始化为 true —— "
            "这正是静默假成功的根源")
        # 允许在注释里提到 success: true（说明历史 bug），但不得作为赋值出现
        for line in src.splitlines():
            code = line.split("//")[0]  # 去掉行内注释
            assert "result.success = true" not in code, (
                "仍存在无条件 `result.success = true`")

    def test_success_computed_from_actual_outcomes(self):
        """success 必须由实际结果推导：已配置的步骤全部成功才算成功。"""
        src = _read(SUBSCRIBE)
        assert "result.subscriber_created || !apiToken" in src
        assert "result.delivered_pdf || !resendApiKey" in src

    def test_pdf_url_always_returned(self):
        """pdf_url 必须始终返回，前端才能做兜底直链。"""
        src = _read(SUBSCRIBE)
        assert "result.pdf_url = magnetUrl" in src

    def test_failure_returns_truthful_error(self):
        """失败路径必须给出可读的 error，而不是静默成功。"""
        src = _read(SUBSCRIBE)
        assert 'if (!result.success)' in src
        assert 'could not be delivered' in src

    def test_not_configured_flags_exposed(self):
        """部署缺口（缺 token）必须显式暴露，不能伪装成成功。"""
        src = _read(SUBSCRIBE)
        assert "result.mailerlite_configured" in src
        assert "result.resend_configured" in src


class TestSubscribeFrontendContract:
    """两个表单曾只判 `resp.ok && data.success` —— 假成功的显示端。"""

    def test_both_forms_exist(self):
        for p in FORMS:
            assert p.exists(), f"缺少 {p}"

    def test_no_form_gates_on_success_alone(self):
        for p in FORMS:
            src = _read(p)
            assert "resp.ok && data.success) {" not in src, (
                f"{p.name} 仍只判 success —— delivered_pdf 为 false 时会误报成功")

    def test_both_forms_check_delivered_pdf(self):
        for p in FORMS:
            src = _read(p)
            assert "data.success && data.delivered_pdf" in src, (
                f"{p.name} 未校验 delivered_pdf")

    def test_both_forms_offer_pdf_fallback_link(self):
        """PDF 邮件没发出去时，必须给客户一条直链，而不是让他干等。
        注意前端是 JS 字符串拼接（'<a href="' + data.pdf_url + '"...），
        所以查拼接片段而不是完整字面量。"""
        for p in FORMS:
            src = _read(p)
            assert "data.pdf_url" in src, f"{p.name} 未使用 pdf_url 兜底"
            assert "'<a href=\"'" in src and '+ data.pdf_url +' in src, (
                f"{p.name} 未把 pdf_url 拼进可点击的 <a href>")

    def test_success_message_only_shown_when_pdf_delivered(self):
        """「your guide is on its way」这句话必须绑定 delivered_pdf。"""
        for p in FORMS:
            src = _read(p)
            ok_line = [l for l in src.splitlines()
                       if "on its way" in l][0]
            # 该文案所在的分支条件必须在它之前几行内出现 delivered_pdf
            idx = src.index(ok_line)
            window = src[max(0, idx - 400):idx]
            assert "delivered_pdf" in window, (
                f"{p.name}: 'on its way' 文案未被 delivered_pdf 门控")
