# ChinaBound Travel - Workflow Architecture & Safety

> Maintained by the P0 governance work (2026-08-12). Update this file whenever a workflow is added, renamed, or its triggers change. The static test `tests/test_workflow_names.py` fails if monitored names drift from the real `name:` fields.

## 1. Workflow Inventory

| Workflow File | Workflow Name (`name:`) | Triggers | Critical? | Error Alert Monitored? | Auto Retry? | Writes Main? | Publishes Content? |
|---|---|---|---|---|---|---|---|
| `deploy-cloudflare-pages.yml` | Post-deploy Tasks | push main (paths: content/**, static/**, layouts/**, themes/**, config/**, hugo.toml) + workflow_dispatch | Yes | Yes | No (manual) | Yes (manifest.json only) | Indirect (deploys site) |
| `weekly-blog-update.yml` | Joran博文生成+双AI自动审核发布 | schedule 00:00 UTC + workflow_dispatch | Yes | Yes | Yes (Retry Failed Jobs) | Yes (content/manifest/config/static) | Yes (blog posts + social) |
| `social_distributor.yml` | Social Media Distributor | schedule 09:00 UTC + workflow_dispatch | Yes | Yes | Yes | No | Yes (social posts) |
| `content-rotation.yml` | Content Rotation Distributor | schedule 02:00/10:00 UTC + workflow_dispatch | Yes | Yes | Yes | Yes (manifest_rotator.json only) | Yes (social rotation) |
| `youtube-auto-publish.yml` | YouTube Auto Publish | schedule Mon 03:00 UTC + workflow_dispatch | Yes | Yes | No (double-upload risk, manual) | No | Yes (YouTube videos) |
| `monthly-ebook-update.yml` | Monthly Ebook Guide Update | schedule 1st 06:00 UTC + workflow_dispatch | Yes | Yes | No | Yes (content/layouts) | Yes (ebook page) |
| `env-check.yml` | Environment Check | schedule 00:00 UTC + workflow_dispatch + pull_request | Medium | No | No | No | No |
| `health-check.yml` | Daily Health Check | schedule 01:00 UTC + workflow_dispatch | Medium | No | No | No | No |
| `purge-cache.yml` | Purge Cloudflare Cache | workflow_dispatch | Low | No | No | No | No |
| `manual-deploy.yml` | Manual Deploy to Cloudflare Pages | workflow_dispatch | Yes | No (manual action) | No | No | Yes (deploys site) |
| `feishu-daily-report.yml` | Feishu Daily Report | schedule 01:00 UTC + workflow_dispatch | Low | No | No | Yes (reports/okr_progress only, [skip ci]) | No |
| `weekly-report.yml` | Weekly Feishu Report | schedule Mon 00:00 UTC + workflow_dispatch | Low | No | No | Yes (reports/okr_progress only, [skip ci]) | No |
| `monthly-report.yml` | Monthly Feishu Report | schedule 1st 00:00 UTC + workflow_dispatch | Low | No | No | Yes (reports/okr_progress only, [skip ci]) | No |
| `quarterly-report.yml` | Quarterly Feishu Report | schedule 1st Jan/Apr/Jul/Oct + workflow_dispatch | Low | No | No | Yes (reports/okr_progress only, [skip ci]) | No |
| `yearly-report.yml` | Yearly Feishu Report | schedule 1 Jan + workflow_dispatch | Low | No | No | Yes (reports/okr_progress only, [skip ci]) | No |
| `deploy-buffer-worker.yml` | Deploy Buffer Worker | push main (paths: buffer-worker/**) + workflow_dispatch | Yes | No (infra, rarely fails) | No | No | No |
| `error-alert.yml` | Error Alert | workflow_run (monitored list) completed | Ops | - | - | No | No |
| `retry-failed.yml` | Retry Failed Jobs | workflow_run (monitored list) completed | Ops | - | - | No | No |

## 2. Trigger Dependency Map

```
push main (content/static/layouts/config/hugo.toml)
   └─▶ deploy-cloudflare-pages.yml (Post-deploy Tasks)
         └─▶ manifest.json commit+push  → does NOT re-trigger deploy (manifest.json not in paths)

weekly-blog-update.yml (schedule)
   └─▶ commit+push main (content/manifest/config/static)
         └─▶ deploy-cloudflare-pages.yml   (intended: content change deploys site)
   └─▶ gh workflow run deploy-cloudflare-pages.yml  (redundant safety net)

content-rotation.yml (schedule)
   └─▶ commit manifest_rotator.json [skip ci] → no re-trigger

feishu/weekly/monthly/quarterly/yearly-report.yml
   └─▶ commit reports/okr_progress [skip ci] → no re-trigger

error-alert.yml / retry-failed.yml (workflow_run)
   └─▶ never trigger other workflows; retry-failed re-dispatches monitored workflows (workflow_dispatch)
         └─▶ retry-failed does NOT re-trigger itself (dispatch events are excluded by if: condition)
```

**No circular triggers exist.** Every workflow that commits back to `main` uses either:
- a path filter that excludes the committed file, or
- a `[skip ci]` commit message, or
- `workflow_dispatch`-only execution.

## 3. Concurrency Rules

| Group | Workflow(s) | cancel-in-progress | Rationale |
|---|---|---|---|
| `post-deploy-tasks` | deploy-cloudflare-pages.yml | `true` | Deploy can be superseded; only the latest deploy matters. |
| `joran-blog-generation` | weekly-blog-update.yml | `false` | Content generation must not be cancelled mid-write; overlapping runs queue. |
| `content-rotation` | content-rotation.yml | `false` | Rotation state/manifest writes must serialize. |
| `social-distributor` | social_distributor.yml | `false` | Avoid double social posting; runs queue. |
| `youtube-auto-publish` | youtube-auto-publish.yml | `false` | Avoid double video upload; runs queue. |
| `retry-failed-jobs` | retry-failed.yml | `false` | Retries must serialize. |

## 4. Workflows that Write `main`

- `deploy-cloudflare-pages.yml` → `manifest.json` only.
- `weekly-blog-update.yml` → `content/posts/`, `content/_draft/`, `manifest.json`, `config/topic_pool.json`, `config/error_knowledge_base.json`, `layouts/shortcodes/`, `static/img/`.
- `content-rotation.yml` → `manifest_rotator.json`.
- Report workflows → `reports/okr_progress/` (with `[skip ci]`).

## 5. Workflows that MUST NOT Trigger Each Other

- `error-alert.yml` must not trigger other workflows (it only alerts).
- `retry-failed.yml` must not retry `youtube-auto-publish.yml` (double upload risk) or itself.
- The deploy workflow's manifest write-back must not re-trigger the deploy workflow — `manifest.json` must stay outside the deploy `paths:` filter.
- Report workflows must keep `[skip ci]` in their commit messages so pushes do not spin up push-triggered workflows.

## 6. Error Alert Coverage (P0-3)

`error-alert.yml` monitors (by exact `name:` field):
`Joran博文生成+双AI自动审核发布`, `Social Media Distributor`, `Content Rotation Distributor`, `YouTube Auto Publish`, `Post-deploy Tasks`, `Monthly Ebook Guide Update`.

`retry-failed.yml` auto-retries (by exact `name:` field):
`Joran博文生成+双AI自动审核发布`, `Social Media Distributor`, `Content Rotation Distributor`.

Note: retrying a workflow re-runs it via `gh workflow run`, which is a `workflow_dispatch` event. `retry-failed.yml` excludes `workflow_dispatch` events from its own trigger, so retry loops are impossible by design.
