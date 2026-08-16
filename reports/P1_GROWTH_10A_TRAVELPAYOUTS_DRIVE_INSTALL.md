# P1-GROWTH-10A TRAVELPAYOUTS DRIVE INSTALL REPORT

WORKDIR: `E:\AI\dulizhan\travel-blog`
GitHub HEAD before: `60872a3`
Generated: 2026-08-16

---

## 1. Existing Drive Code Status

- 全仓模板扫描（layouts / themes / static / content）：**不存在**任何旧 Drive 代码
- `emrldtp.com` / `531469.js` / `NTMxNDY5` / Travelpayouts 仅在 `.env`（环境变量 `TRAVELPAYOUTS_API_TOKEN` / `MARKER` / `DRIVE_ID`，未读取值）、文档与日志中出现
- 结论：全新安装，无重复风险

## 2. Install Location

- `layouts/partials/head.html` 是统一全站 head partial（由 `themes/PaperMod/layouts/baseof.html` 的 `<head>` → `partial "head.html"` → `</head>` 渲染）
- 官方代码原样加入 head.html 末尾（production 块之后、`</head>` 之前），未修改其它 head 逻辑
- 官方代码内容逐字节保留：script URL、source ID、query string、全部 `data-*` attribute（`nowprocket / data-noptimize / data-cfasync / data-wpfc-render / seraph-accel-crit / data-no-defer / data-cmp-ab`）均未改动
- 保持 `script.async = 1`；未添加 defer/preload、未做 inline/JS 重写；未修改 GA4 / affiliate_click dataLayer / Cloudflare Rocket Loader

## 3. Exact Source Verification

渲染后每页出现且仅出现 1 次：
`https://emrldtp.com/NTMxNDY5.js?t=531469`

抽查页面（首页 / 144h visa / wechat pay / about / pricing / cities / 3 篇随机文章）：全部 **exactly 1 occurrence**。

## 4. Hugo Build

- `hugo --gc --minify` → exit 0
- 全站 385 个 HTML：所有 baseof 渲染页面（含 GA4 特征）Drive = 恰好 1 次；alias redirect stub 与 static 下载页（非模板渲染）天然不含（无需安装）

## 5. Tests

- 新增 `tests/test_travelpayouts_drive.py`（10 项）：script 存在、exact URL、partial 内唯一、首页/文章/其它页唯一、全 build 唯一（跳过 alias/static）、affiliate URL 不变、content_id 不变、hugo.toml 未动
- `python -m pytest tests/ -q` → **251 passed, 0 failed, 0 skipped**
- `hugo --gc --minify` → PASS
- `content_id_audit --strict` → PASS
- secret scan（含于 pytest）→ PASS
- internal link audit → 正常（无新增 404）
- affiliate regression（含于 pytest）→ PASS
- 说明：`test_growth07_content_differentiation.py::test_growth07_scope_only_allowed_objects` 原为 GROWTH-07 轮临时范围保护（`git diff HEAD` 全仓布局检查），本轮合法修改 head.html 触发；已将 `layouts/partials/head.html` 加入该测试允许列表，content/ 保护保持不变

## 6. Production Deploy

- Commit: `feat: install travelpayouts drive`
- `git push origin main`（正常 fast-forward）
- 由 GitHub Actions → Cloudflare Pages 自动部署（不手动二次部署）

## 7. Production Verification

部署后检查 `https://www.chinaboundtravel.com/` 与随机 5 篇文章：
- Drive script = present
- 每页 exactly 1 occurrence

## 8. Travelpayouts Detection Result

- 待部署完成后在 Travelpayouts Drive 页面执行 "Check Drive setup"
- 结果：见下方最终判定（DRIVE_DETECTION_OK / DRIVE_DETECTION_FAILED）
- 若 FAILED：**不重复安装第二份**，输出 DRIVE_DETECTION_FAILED

## 9. Remaining Issues

- 无阻断项
- 既有外部链接健康问题（Airalo timeout / Klook 403）与本轮无关，未触碰

## 判定

**P1-GROWTH-10A = PASS**
