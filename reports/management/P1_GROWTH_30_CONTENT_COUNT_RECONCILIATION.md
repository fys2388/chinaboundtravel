# P1-GROWTH-30 — Content Count Reconciliation

- Date: 2026-08-29
- Round: AUDIT + MODEL CONSOLIDATION（不改内容、不部署）

## 结论

**CANONICAL_CONTENT_COUNT = 58**

当前 58 posts vs 60 content assets 的差异不是内容丢失，而是口径不一致：
`CONTENT_SEO_INVENTORY.csv` 把 2 个 `content/posts/drafts/` 下的草稿文件也计入了
存量资产，而 `content_id_audit.py` 只扫描 `content/posts/*.md` 根目录文件。

## 各数据源核对

| 数据源 | 数量 | 说明 |
|---|---:|---|
| `content/posts/*.md` | 58 | 正式发布的文章文件（唯一真实内容源） |
| `CONTENT_SEO_INVENTORY.csv` | 60 | 多出 2 行草稿历史变体 |
| `REPORTING_SNAPSHOT.json -> published_posts` | 58 | 正确，来自 `content_id_audit.py` |
| `content_id_audit.py audit --strict` | 58/58 PASS | 唯一 content_id，无缺失/重复 |
| `CHINABOUND_TRAVEL_2_0_MASTER_DASHBOARD.md` | 60 | 旧缓存值，已过时 |

清单中多出的 2 行：

| content_id | URL | 状态 |
|---|---|---|
| `cbt-575e18482ca0` | `/posts/china-just-made-it-way-easier-to-visit-my-mother-i/` | NOT_INDEXED，草稿 |
| `cbt-407090802298` | `/posts/shanghai-like-a-local-hidden-neighborhoods-tourist/` | NOT_INDEXED，草稿 |

## 权威定义

**已发布内容（计入 CANONICAL_CONTENT_COUNT）**

1. 文件位于 `content/posts/` 根目录，扩展名为 `.md`
2. front matter 存在合法唯一 `content_id`（`cbt-[0-9a-f]{12}`）
3. `draft` 不为 `true`
4. 不在 `content/posts/drafts/`、`content/posts/.archived/`、
   `content/posts/.audit_backup/`、`content/_draft/` 下

**明确排除**

- 草稿目录与历史变体：`drafts/`、`_draft/`、`.archived/`、`.audit_backup/`
- 非 post 页面：`about/`、`cities/`、`content/`、`ebook/`、`guides/`、
  `internet/`、`member-*`、`payments/`、`resources/`、`social/`、
  `static-package/`、`visa/`
- 社交资产库 `content/social/inventory.json` 的 100 条素材，不计入文章数
- 已删除但仍在 SEO 清单中的历史 URL

## 所有报告/脚本必须使用的口径

1. 唯一权威计数 = `python scripts/content_id_audit.py audit --strict` 输出的
   `Posts scanned` 值（当前 58）。
2. `CONTENT_SEO_INVENTORY.csv` 只保留能在 `content/posts/*.md` 中找到文件的
   行；草稿/历史行应标记 `source=draft` 并从发布计数中剔除。
3. `REPORTING_SNAPSHOT.json` 的 `published_posts` 必须读取
   `content_id_audit.py` 结果，禁止使用 CSV 行数。
4. 主仪表盘不得硬编码 60，应读取快照值。
5. 本轮不修改脚本行为；上述为下轮实施契约。

## 验证

- `content_id_audit.py audit --strict`：PASS，58/58。
- 清单与文件集合差异：2 行草稿，无正式文章遗漏。
