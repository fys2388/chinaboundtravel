/**
 * Buffer 社区评论云端巡检脚本（方案A）
 *
 * 功能：
 *  1. --login     首次运行：打开 Buffer 登录页，用户人工登录一次，保存 storageState
 *  2. 默认/巡检    加载 storageState，打开社区收件箱，检测未答复评论，
 *                  用 SenseNova LLM 生成英文回复并提交
 *  3. --dry-run   只检测不回复（打印将回复的评论）
 *
 * 用法：
 *  node patrol.mjs --login          # 首次：人工登录一次
 *  node patrol.mjs --dry-run        # 巡检但不回复
 *  node patrol.mjs                  # 巡检并自动回复
 *
 * 环境变量：
 *  SENSENOVA_API_KEY  必填（生成回复用）
 *  STORAGE_STATE_PATH 可选（默认 .storage-state.json）
 */
import { chromium } from 'playwright';
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { createHash } from 'node:crypto';
import { generateReply } from './llm.mjs';

const __dirname = dirname(fileURLToPath(import.meta.url));

// ============ 参数解析 ============
const args = process.argv.slice(2);
const FLAGS = {
  login: args.includes('--login'),
  dryRun: args.includes('--dry-run'),
  state: argValue('--state') || process.env.STORAGE_STATE_PATH || join(__dirname, '.storage-state.json'),
  config: argValue('--config') || join(__dirname, 'config.json'),
  processed: argValue('--processed') || join(__dirname, 'processed.json'),
};

function argValue(name) {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : null;
}

// ============ 配置加载 ============
function loadConfig() {
  const cfg = JSON.parse(readFileSync(FLAGS.config, 'utf8'));
  cfg.statePath = FLAGS.state;
  cfg.processedPath = FLAGS.processed;
  cfg.sensenovaApiKey = process.env.SENSENOVA_API_KEY || '';
  return cfg;
}

// ============ 工具 ============
const hash = (s) => createHash('sha256').update(s).digest('hex').slice(0, 16);

function loadProcessed() {
  if (!existsSync(FLAGS.processed)) return new Set();
  try {
    return new Set(JSON.parse(readFileSync(FLAGS.processed, 'utf8')));
  } catch {
    return new Set();
  }
}
function saveProcessed(set) {
  writeFileSync(FLAGS.processed, JSON.stringify([...set], null, 2));
}

const log = (...a) => console.log('[patrol]', ...a);
const warn = (...a) => console.warn('[patrol][warn]', ...a);

// ============ 登录模式 ============
async function runLogin(cfg) {
  log('打开登录页，请在弹出的浏览器中登录 Buffer...');
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  await page.goto(cfg.loginUrl, { waitUntil: 'domcontentloaded' });
  log('登录完成后，等待你在浏览器里按回车确认（或等待页面跳转到 publish.buffer.com 主页）...');
  // 等待用户完成登录：跳转到 publish.buffer.com 且出现侧边栏/主页标志
  try {
    await page.waitForURL(/publish\.buffer\.com\/.*(home|channels|dashboard|plan|$)/, { timeout: 5 * 60 * 1000 });
  } catch {
    log('未检测到跳转，尝试保存当前状态...');
  }
  await page.waitForTimeout(2000);
  const state = await page.context().storageState();
  writeFileSync(cfg.statePath, JSON.stringify(state, null, 2));
  log(`登录态已保存到 ${cfg.statePath}`);
  await browser.close();
  log('完成。后续可用 `node patrol.mjs` 或 `node patrol.mjs --dry-run` 巡检。');
}

// ============ 评论定位 helper ============
// 展开一条评论的回复表单：点击评论正文按钮（含较长文本），等待 textarea 出现
async function expandReplyForm(page, listItem) {
  // 评论正文通常是 listitem 内 textContent 较长的 button/可点击元素
  const candidates = listItem.locator('button').filter({ hasText: /\S{20,}/ });
  const count = await candidates.count();
  for (let i = 0; i < count; i++) {
    const btn = candidates.nth(i);
    const text = (await btn.textContent() || '').trim();
    // 跳过明显非正文按钮（如 Like/Copy link/Reply/用户名短按钮）
    if (/^(like|copy|reply|resolve|d$|@\w{1,20}$)/i.test(text)) continue;
    if (text.length >= 20) {
      try {
        await btn.click({ timeout: 5000 });
        await page.waitForTimeout(500);
        return { clicked: true, clickedText: text };
      } catch {
        /* 点击失败则尝试下一个 */
      }
    }
  }
  return { clicked: false };
}

// 从评论线程提取评论者（来自 aria-label）与评论正文（来自文本）
function extractIdentity(groupText, ariaLabel = '') {
  let commenter = '';
  const from = ariaLabel.match(/from\s+([A-Za-z0-9_.-]+)/i);
  if (from) commenter = from[1];
  if (!commenter) {
    const at = groupText.match(/@([A-Za-z0-9_]{1,30})/g);
    if (at) commenter = at[at.length - 1].replace('@', '');
  }
  // 评论正文：取含 @mention 且较长的段落
  const lines = groupText.split(/\n+/).map((s) => s.trim()).filter(Boolean);
  const body = lines.find((l) => l.length >= 15 && /@|[\u4e00-\u9fa5]/.test(l) && !/^(open in|copy|like|reply|resolve)/i.test(l)) || lines.find((l) => l.length >= 20) || groupText;
  return { commenter, commentText: body.slice(0, 500) };
}

// 切换到评论视图（聚合所有帖子的评论）
async function trySwitchToCommentsView(page) {
  const switchBtn = page.locator('button, [role="radio"], label').filter({ hasText: /switch to comments|评论视图/i }).first();
  if (await switchBtn.count()) {
    await switchBtn.click({ timeout: 6000 }).catch(() => {});
    await page.waitForTimeout(2500);
    return;
  }
  const commentsTab = page.locator('[role="tab"]').filter({ hasText: /^Comments/i }).first();
  if (await commentsTab.count()) {
    await commentsTab.click({ timeout: 6000 }).catch(() => {});
    await page.waitForTimeout(2500);
  }
}

// 在页面中找当前已展开的、待回复的空 textarea
async function findReplyTextarea(page) {
  const tas = page.locator('textarea');
  const n = await tas.count();
  for (let i = 0; i < n; i++) {
    const ta = tas.nth(i);
    const ph = await ta.getAttribute('placeholder').catch(() => '');
    if (/reply|回复/i.test(ph || '')) {
      const val = await ta.inputValue().catch(() => '');
      if (!val.trim()) return ta; // 空 textarea = 未答复
    }
  }
  return null;
}

// 填入回复并点击 Reply 提交
async function fillAndReply(page, textarea, replyText) {
  await textarea.click();
  await textarea.fill(replyText);
  await page.waitForTimeout(400);
  // Reply 按钮：在 textarea 所在 form 附近找 "Reply"
  const replyBtn = page.locator('button').filter({ hasText: /^Reply$/i }).last();
  if (await replyBtn.count() === 0) {
    throw new Error('未找到 Reply 按钮');
  }
  await replyBtn.click();
  await page.waitForTimeout(1500);
}

// ============ 巡检主逻辑 ============
async function runPatrol(cfg) {
  const apiKey = cfg.sensenovaApiKey;
  if (!apiKey) {
    warn('SENSENOVA_API_KEY 未设置；将跳过回复生成（仅 dry-run 检测）');
  }
  if (!existsSync(cfg.statePath)) {
    throw new Error(`未找到登录态 ${cfg.statePath}，请先运行: node patrol.mjs --login`);
  }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ storageState: cfg.statePath });
  const page = await context.newPage();
  page.setDefaultTimeout(cfg.actionTimeoutMs || 15000);

  const processed = loadProcessed();
  const replies = [];
  const errors = [];

  log(`打开社区收件箱: ${cfg.communityUrl}`);
  await page.goto(cfg.communityUrl, { waitUntil: 'domcontentloaded' });
  // 等待收件箱主区加载
  await page.waitForSelector('main, [role="main"]', { timeout: cfg.navTimeoutMs || 30000 });
  await page.waitForTimeout(3000);

  // 检测是否登录失效
  const loginHint = await page.locator('text=/log in|sign in/i').count();
  if (loginHint > 0) {
    warn('检测到登录页，登录态可能已过期，请重新运行 --login');
    await browser.close();
    process.exitCode = 2;
    return;
  }

  // 1) 切换到评论视图（聚合所有帖子评论）
  await trySwitchToCommentsView(page);
  await page.waitForTimeout(2000);

  // 2) 定位所有未答复评论线程（aria-label 含 needs attention）
  const pendingGroups = page.locator('[aria-label*="needs attention" i]');
  let count = await pendingGroups.count();
  log(`检测到未答复评论线程: ${count}`);

  // 兜底：若评论视图为空，尝试直接定位（不切视图）
  if (count === 0) {
    const alt = page.locator('[aria-label*="needs attention" i]');
    count = await alt.count();
  }

  let done = 0;
  for (let i = 0; i < count && done < cfg.maxRepliesPerRun; i++) {
    const g = pendingGroups.nth(i);
    const aria = (await g.getAttribute('aria-label').catch(() => '')) || '';
    const groupText = (await g.textContent().catch(() => '')) || '';
    const { commenter, commentText } = extractIdentity(groupText, aria);
    if (!commenter && commentText.length < 15) {
      log(`评论信息不足，跳过`);
      continue;
    }

    const key = hash(`${commenter}|${commentText}`);
    if (processed.has(key)) {
      log(`跳过已处理评论: ${commenter}`);
      continue;
    }

    // 3) 展开回复表单（点击评论正文长文本按钮）
    const exp = await expandReplyForm(page, g);
    if (!exp.clicked) {
      log(`无法展开评论（${commenter}），跳过`);
      continue;
    }

    const ta = await findReplyTextarea(page);
    if (!ta) {
      log(`评论无空回复框（可能已回复/已解决）: ${commenter}，跳过`);
      continue;
    }

    log(`发现未答复评论: ${commenter} — ${commentText.slice(0, 60)}...`);
    const postText = groupText;

    if (FLAGS.dryRun) {
      replies.push({ commenter, commentText, reply: '[dry-run 不回复]' });
      log(`[dry-run] 将回复 ${commenter}`);
      done++;
      continue;
    }

    // 4) 生成回复
    let replyText;
    try {
      replyText = await generateReply({
        commentText,
        commenter,
        postText,
        brandContext: cfg.brandContext,
        charLimit: cfg.replyCharLimit || 280,
        apiKey,
      });
    } catch (e) {
      errors.push({ commenter, err: e.message });
      warn(`生成回复失败 (${commenter}): ${e.message}`);
      continue;
    }

    // 5) 填入并提交
    try {
      await fillAndReply(page, ta, replyText);
      replies.push({ commenter, commentText, reply: replyText });
      processed.add(key);
      saveProcessed(processed);
      log(`✅ 已回复 ${commenter}: ${replyText.slice(0, 50)}...`);
      done++;
    } catch (e) {
      errors.push({ commenter, err: e.message });
      warn(`提交回复失败 (${commenter}): ${e.message}`);
    }
  }

  await browser.close();

  // ============ 汇总 ============
  log('========== 巡检汇总 ==========');
  log(`发现未答复评论: ${replies.length}`);
  log(`成功回复: ${replies.filter((r) => r.reply !== '[dry-run 不回复]').length}`);
  log(`错误: ${errors.length}`);
  if (replies.length) {
    log('--- 回复明细 ---');
    for (const r of replies) log(` • ${r.commenter}: ${(r.reply || '').slice(0, 80)}`);
  }
  if (errors.length) {
    log('--- 错误明细 ---');
    for (const e of errors) log(` • ${e.commenter}: ${e.err}`);
  }
  if (FLAGS.dryRun) log('（dry-run 模式：未实际回复）');
}

// ============ 入口 ============
async function main() {
  const cfg = loadConfig();
  if (FLAGS.login) {
    await runLogin(cfg);
  } else {
    await runPatrol(cfg);
  }
}

main().catch((e) => {
  console.error('[patrol][fatal]', e);
  process.exitCode = 1;
});
