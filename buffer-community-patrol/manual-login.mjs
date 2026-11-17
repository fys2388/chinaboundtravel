/**
 * 人工登录（弹窗）：用户在弹出的 Chromium 窗口里完成 Buffer 登录，
 * 脚本检测登录成功后保存 storageState，并验证目标频道可访问。
 * 用法：node manual-login.mjs
 */
import { chromium } from 'playwright';
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const statePath = join(__dirname, '.storage-state.json');
const COMMUNITY_URL = 'https://publish.buffer.com/channels/6a202882c687a22dd45735b6/community/';

const browser = await chromium.launch({ headless: false });
const page = await browser.newPage();
page.setDefaultTimeout(30000);

await page.goto('https://publish.buffer.com/', { waitUntil: 'domcontentloaded' });
console.log('请在弹出的浏览器窗口中登录 Buffer（fys2388@gmail.com）。脚本会等待你完成登录（最长 10 分钟）...');

let ok = false;
for (let i = 0; i < 100; i++) {
  await page.waitForTimeout(6000);
  const url = page.url();
  const hasSidebar = await page.locator('a:has-text("Community"), a:has-text("Create")').count();
  const hasLogin = await page.locator('input[name=email]').count();
  if (hasSidebar > 0 && hasLogin === 0 && /publish\.buffer\.com/.test(url)) {
    ok = true;
    break;
  }
  if (i % 10 === 0) console.log(`等待登录... (${i * 6}s) ${url.slice(0, 60)}`);
}
if (!ok) {
  console.error('登录未完成（超时）。请重试。');
  await browser.close();
  process.exit(1);
}

const state = await page.context().storageState();
writeFileSync(statePath, JSON.stringify(state, null, 2));
console.log(`登录成功，storageState 已保存 (${state.cookies.length} cookies)`);

// 验证目标频道可访问
await page.goto(COMMUNITY_URL, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(6000);
const restricted = await page.locator('text=Access restricted').count();
if (restricted > 0) {
  console.error('⚠️ 登录成功，但目标频道仍显示 Access restricted（可能该账户无此频道权限）');
} else {
  console.log('✅ 目标频道可访问');
}
await browser.close();
