# 定时草稿发布批次清单

发布策略：每批 = 移动 `content/_draft/<file>` → `content/posts/<slug>.md`，
改 front-matter `draft: "true" → false`，`audit_status: pending → pass2`，
本地 `hugo build` 验证后 git 提交推送（Cloudflare Pages 自动部署），
最后用 `scripts/gsc_index_submit.py` 提交新 URL。

发前必查：目标 slug 在 `content/posts/` 无同名文件、content_id 无重复。

## 批次 1（明天 2026-10-03）
- 源文件: `content/_draft/2026-08-23-kung-fu-and-martial-arts-in-china-where-to-see-and-train-guide-attempt3.md`
- 目标 slug: `kung-fu-and-martial-arts-in-china`
- 目标路径: `content/posts/kung-fu-and-martial-arts-in-china.md`
- 理由: 独特卖点（功夫/武术），旅游长尾，低竞争，差异化内容
- GSC URL: https://www.chinaboundtravel.com/posts/kung-fu-and-martial-arts-in-china/

## 批次 2（后天 2026-10-04）
- 源文件: `content/_draft/2026-08-23-china-solo-travel-guide-safety-hostels-and-making-friends-attempt2.md`
- 目标 slug: `china-solo-travel-guide-safety-hostels-and-making-friends`
- 目标路径: `content/posts/china-solo-travel-guide-safety-hostels-and-making-friends.md`
- GSC URL: https://www.chinaboundtravel.com/posts/china-solo-travel-guide-safety-hostels-and-making-friends/

- 源文件: `content/_draft/2026-08-26-china-travel-etiquette-tipping-photos-and-unwritten-rules-guide-attempt1.md`
- 目标 slug: `china-travel-etiquette-tipping-photos-and-unwritten-rules-guide`
- 目标路径: `content/posts/china-travel-etiquette-tipping-photos-and-unwritten-rules-guide.md`
- GSC URL: https://www.chinaboundtravel.com/posts/china-travel-etiquette-tipping-photos-and-unwritten-rules-guide/

## 排除项
- `china-business-travel-guide ... attempt2`: slug/content_id/canonical 与已发布
  `2026-08-30-china-business-travel-guide-...md` 完全重复，会 Hugo 冲突，不发布。

## 执行命令模板（每批）
```
cd E:\AI\dulizhan\travel-blog
Move-Item content/_draft/<src>.md content/posts/<slug>.md
# 编辑 front-matter: draft: "true" → draft: false ; audit_status: pending → pass2
hugo build 2>&1 | Select-Object -Last 5   # 必须无 ERROR、Pages 数 +N
python scripts/gsc_index_submit.py --optimized
git add -A
git commit -m "feat(content): publish <slug>"
git pull --rebase origin main
git push origin main
```

## 状态
- [ ] 批次 1（2026-10-03）kung-fu-martial-arts
- [ ] 批次 2（2026-10-04）china-solo-travel + china-travel-etiquette
