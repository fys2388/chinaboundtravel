# 144 小时过境免签文章 · 事实核验清单

- 日期: 2026-09-20
- 目标文章: `content/posts/144-hour-visa-free-transit-guide.md`（content_id `cbt-b4ff4381a014`）
- 性质: **只建清单，不改正文**。正文属保护区且需 owner 复核后才能改。
- 方法: 全部判据走本地权威数据（文章 front-matter、`static/_redirects`、
  `reports/content_audit/P1_GROWTH_30R_FACT_CHECK_QUEUE.csv`、
  `reports/content_rebuild/FACT_CHECK_QUEUE.csv`）。标记为 **[确认]** 的条目
  无需外部访问即可判定；标记 **[待核]** 的条目需要权威来源在线核对。

---

## 一、[确认] front-matter 的 `fact_checked` 是无证据声明

front-matter 声明:

```yaml
fact_checked: "2026-09-13"
reviewed_by: "ChinaBound Travel Editorial Team"
reviewed_at: "2026-09-13"
last_updated: "2026-09-15"
```

但 `reports/content_audit/P1_GROWTH_30R_FACT_CHECK_QUEUE.csv` 里该文所有行的
`source_status` 都是 `NO_VERIFIED_SOURCE`，`action` 都是 `VERIFY_OR_REMOVE`：

| 类别 | 建议 | source_status | evidence_required | action |
|---|---|---|---|---|
| prices / fees | 动态事实关键词 'cost' | NO_VERIFIED_SOURCE | 官方费率表及核验日期 | VERIFY_OR_REMOVE |
| law / regulation | 动态事实关键词 'policy' | NO_VERIFIED_SOURCE | 官方法规原文及生效日期 | VERIFY_OR_REMOVE |
| visa / immigration | 动态事实关键词 'visa' | NO_VERIFIED_SOURCE | 官方签证/出入境页面 | VERIFY_OR_REMOVE |
| visa / immigration | 动态事实关键词 'passport' | NO_VERIFIED_SOURCE | 官方签证/出入境页面 | VERIFY_OR_REMOVE |

**范围更大**：该队列 479 行，`NO_VERIFIED_SOURCE` 占 **479/479（100%）**——
全站没有任何一条动态事实被核验过。而声明 `fact_checked` 的文章有 3 篇，
全部落在这个队列内。

两个衍生问题：
1. `fact_checked` (09-13) **早于** `last_updated` (09-15)——文章在最后一次
   「事实核验」之后又被改过，核验结论已失效。
2. `reviewed_by` 是一个不可追溯的团队署名，没有对应的人或记录。

**建议**：在队列清掉之前不要保留 `fact_checked` 字段，或改成
`fact_checked: "2026-09-13 (unverified — see P1_GROWTH_30R_FACT_CHECK_QUEUE.csv)"`。
这是 owner 决策项，因为删字段会改变文章元数据契约。

---

## 二、[确认] L81 来源错误归因（香港入境处 ≠ 中国国家移民管理局）

```markdown
**>>> [Check the full list of eligible ports on China Immigration]
        (https://www.immd.gov.hk/eng/visa_descriptions/china-144-hour-visa-free.html) <<<**
```

`immd.gov.hk` 是**香港特别行政区入境事务处（Immigration Department, HKSAR）**的
域名，不是中国国家移民管理局。144 小时过境免签是**内地**政策，口岸清单由
NIA 发布（`https://en.nia.gov.cn/`）——这个 URL 在 front-matter 的 `sources`
里确实列了，但正文的关键行动链接却指向香港。

一个香港政府域名无法是内地过境免签口岸清单的权威来源。这不是措辞问题，
是把权威来源指错给了另一个司法辖区的主管部门。

**建议**：改为 NIA 官方页面，并加上口岸清单的公布日期。

---

## 三、[确认] L62 机场 IATA 代码写错

```markdown
- **Beijing Capital Airport** (PEK/PKX)   <- L62  多写了 PKX
- **Beijing Daxing Airport** (PKX)        <- L63  正确
```

PEK = 北京首都国际机场，PKX = 北京大兴国际机场。L62 把两个机场的代码都写在
了首都机场后面，读者按 PKX 查首都机场会得到大兴的结果。

**建议**：L62 改为 `(PEK)`。这是低风险修复，但正文属保护区，需 owner 点头。

---

## 四、[待核] "55+ eligible countries" 链接到私营中介

L53:

```markdown
China offers a **144-hour (6-day) visa exemption** for travelers from
[55+ eligible countries](https://www.visaforchina-cbp.com/)
```

问题两点：
1. `visaforchina-cbp.com` 是私营签证服务中介，不是发布名单的机构。
2. "55+" 是模糊表述——NIA 公布的是具体国名清单，且有明确的最近一次扩围日期。
   模糊数字在政策类文章里会随时间自然过期，且无法被核验。

**待核**：需要 owner 从 NIA 官方页面取到当前确切国数与最近一次扩围日期，
再决定是否改为具体数字 + 生效日期。

---

## 五、[待核] 三处无法核验的具体主张

| 行 | 主张 | 为什么需要核 |
|---|---|---|
| L65 | `Beijing West Railway Station (for select European tours)` | 铁路口岸是 144 小时政策里最不常见的入口，且限定了"特定欧洲团"，属于强约束主张，必须有原文依据 |
| L79 | `Many more cities added in 2024-2025 expansion` | 无城市数、无清单、无来源。政策扩围是有具体公告的，这句话等于把可核验事实写成了模糊叙述 |
| L88 | `US, UK, Canada, Australia, Japan, most EU, and many more` | "most EU" 无法核验——具体是哪些成员国 |

---

## 六、[确认] `{{< soft-recommend >}}` 泄漏到 meta description

L13:

```yaml
description: '{{< soft-recommend partner="esim" topic="visa" placement="articlemid1"
            text="See eSIM options" >}} Keeping your phone connected in China...'
```

Hugo shortcode 写在 `description` 字段里不会被渲染展开——shortcode 只在
content 区解析。结果是**原始模板语法直接进入 `<meta name="description">`**，
在搜索摘要、社交分享、以及任何读取 meta 的工具里都会显示 `{{< soft-recommend ... >}}`。

这是全站已知缺陷（`reports/seo/OG_TAG_AUDIT.md` 已记录）：`{{< soft-recommend >}}`
残留在 2 篇文章里，泄漏进 6 个 meta tag。

**建议**：把 shortcode 从 `description` 移到正文对应位置，`description` 只留纯文本。

---

## 七、执行顺序建议

1. **先做三**（L62 机场代码）和**六**（description shortcode）——低风险、
   明确、无争议。但正文属保护区，仍需 owner 明确授权。
2. **做二**（L81 来源归因）——改一个链接，风险低，收益高（权威来源指错辖区）。
3. **处理一**（`fact_checked` 字段）——需要 owner 决定是删字段还是加注。
4. **四、五** 需要在线核对 NIA 官方清单后才能改，本会话无外部核验通道。

## 八、本清单没有做的事

- 没有修改 `content/posts/` 下任何文件（保护区，且需 owner 复核）
- 没有删除或改写 `fact_checked` 字段
- 没有把 `[待核]` 条目当成已确认结论——它们需要权威来源在线核对
