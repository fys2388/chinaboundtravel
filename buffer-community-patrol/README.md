# Buffer 社区评论云端巡检（方案A）

用 Playwright 打开 Buffer 社区收件箱，检测未答复评论，用 SenseNova LLM 生成英文回复并自动提交。

## 原理

Buffer 的**公开 GraphQL API 不提供社区评论的读取/回复接口**（已核查 `developers.buffer.com`：无 comment/reply/community 读写操作）。因此方案A采用**浏览器自动化**：云端（GitHub Actions cron）用已登录会话打开社区收件箱，操作页面完成检测与回复，行为等同人工。

## 目录

| 文件 | 说明 |
|---|---|
| `patrol.mjs` | 主巡检脚本（登录 / 巡检 / dry-run） |
| `llm.mjs` | SenseNova LLM 客户端（生成英文回复） |
| `config.json` | 配置（社区 URL、频道、品牌语境、回复上限） |
| `.storage-state.json` | 登录态 Cookie（**敏感，gitignore，不提交**） |
| `processed.json` | 已回复评论指纹（gitignore） |

## 首次使用

```bash
cd buffer-community-patrol
npm install
npx playwright install chromium      # 下载 Chromium（首次）
node manual-login.mjs                # 弹窗人工登录 Buffer（已执行，登录态已保存）
```

登录后 `.storage-state.json` 自动保存，后续巡检复用。登录态会过期（Buffer 会话失效时），需重跑 `node manual-login.mjs`。

> 注：Buffer-A 账户为 `fys2388@gmail.com`（拥有 X 频道 fys2388，id `6a202882c687a22dd45735b6`）；`1558835921@qq.com` 是 Buffer-B（Pinterest，账户 id `6a20329943b37a7289e25b6b`），**不是**目标频道所有者。

## 巡检

```bash
node patrol.mjs --dry-run    # 只检测不回复（先看将回复哪些）
node patrol.mjs              # 检测 + 自动回复
```

## 云端定时（GitHub Actions）

`../.github/workflows/buffer-community-patrol.yml` 已提供每日两次（UTC 02:00 / 14:00）定时。需在 GitHub 仓库配置 secrets：

- `SENSENOVA_API_KEY`：SenseNova API Key（生成回复用）
- `BUFFER_STORAGE_STATE`：`.storage-state.json` 的 base64（登录态）。生成：`powershell "[Convert]::ToBase64String([IO.File]::ReadAllBytes('.storage-state.json'))"`，把输出粘贴到 secret

配置后 workflow 每次运行用该登录态巡检并回复。若登录态过期（Buffer 登录失效），重跑 `node manual-login.mjs` 更新 secret。

> GitHub 仓库：`fys2388/chinaboundtravel`。配置 secret 可在 GitHub 网页 `Settings → Secrets and variables → Actions` 手动添加，或用 `gh secret set ...`（需 `gh auth refresh` 重新认证，当前 keyring token 已失效）。

## 注意

- 登录态含 Cookie，**绝不提交 git**。
- 自动回复前建议先 `--dry-run` 观察回复内容是否贴切。
- 若想人工把关，可改用「仅通知」模式：脚本只输出新评论，由人工确认后再回复。
