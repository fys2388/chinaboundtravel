# Canonical Conflict Queue

> 状态更新：2026-08-31 — 6 个 canonical 冲突已全部解决并线上验证通过（详见下方 RESOLVED 表）。
> 历史：Candidates detected via URL Inspection API (google_canonical != user_canonical)。当时未做修改。

## ✅ RESOLVED — 6 个冲突验证结果

| url | 解决方式 | 线上验证 (2026-08-31) | sitemap | 状态 |
|---|---|---|---|---|
| /posts/a-gastronomic-adventure-in-china-food-recommendations-for-international-travelers/ | 301 → /posts/food-recommendations-guide/ | HTTP 301, Location 正确 | 已排除 | ✅ RESOLVED |
| /posts/chinabound-travel-guide-2026-07-monthly-update/ | canonicalURL 已统一为 www 自引用 | HTTP 200, `<link rel=canonical href=https://www.chinaboundtravel.com/posts/chinabound-travel-guide-2026-07-monthly-update/>` | 在 sitemap（活页） | ✅ RESOLVED |
| /posts/navigating-china-with-confidence-a-californians-guide-to-travel-safety/ | 301 → /posts/is-china-safe-for-tourists-2026-honest-safety-assessment/ | HTTP 301, Location 正确 | 已排除 | ✅ RESOLVED |
| /posts/transportation-guide-guide/ | 301 → /posts/china-transportation-complete-guide-trains-subways-taxis-and-more/ | HTTP 301, Location 正确 | 已排除 | ✅ RESOLVED |
| /posts/transportation-guide/ | 301 → /posts/china-transportation-complete-guide-trains-subways-taxis-and-more/ | HTTP 301, Location 正确 | 已排除 | ✅ RESOLVED |
| /posts/travel-safety-guide/ | 301 → /posts/is-china-safe-for-tourists-2026-honest-safety-assessment/ | HTTP 301, Location 正确 | 已排除 | ✅ RESOLVED |

## 解决机制

1. **5 个重复/遗留 URL**：通过 `static/_redirects`（Cloudflare Pages）301 永久重定向到唯一 canonical 目标页。
2. **1 个活页 canonical 修复**：`chinabound-travel-guide-2026-07-monthly-update` 的 front matter `canonicalURL` 已从非 www 修正为 www 自引用。
3. **canonical 目标页健康**：`/posts/food-recommendations-guide/`、`/posts/is-china-safe-for-tourists-2026-honest-safety-assessment/`、`/posts/china-transportation-complete-guide-trains-subways-taxis-and-more/` 均 HTTP 200 且带正确 www 自引用 canonical。
4. **sitemap 一致**：5 个重定向 URL 已从 sitemap 排除，仅保留 canonical 活页（66 个 URL）。

## 后续动作（如需加速 Google 重新评估）

- 使用 GSC Index Submit / URL Inspection 对上述 6 个 URL 提交重新抓取（re-inspection），Google 将按 301 + canonical 信号收敛。
- 本轮 6 个冲突已解决；若后续 URL Inspection 报告出现新的 google_canonical != user_canonical，再追加到此队列。
