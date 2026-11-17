/**
 * 自动登录 Buffer 并保存 storageState（凭据经环境变量传入，不落盘）
 * 用法：BUFFER_EMAIL=xxx BUFFER_PASSWORD=xxx node auto-login.mjs
 */
import { chromium } from 'playwright';
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const statePath = join(__dirname, '.storage-state.json');
const email = process.env.BUFFER_EMAIL || '';
const password = process.env.BUFFER_PASSWORD || '';
if (!email || !password) {
  console.error('缺少 BUFFER_EMAIL / BUFFER_PASSWORD');
  process.exit(1);
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
page.setDefaultTimeout(30000);

await page.goto('https://publish.buffer.com/', { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(3000);

// 若已登录则直接保存
const already = await page.locator('input[name=email]').count();
if (already === 0) {
  console.log('已处于登录态，直接保存');
} else {
  await page.fill('input[name=email]', email);
  await page.fill('input[name=password]', password);
  await page.locator('button:has-text("Continue")').click();
  console.log('已提交登录，等待跳转...');
}

// 等待登录成功：回到 publish.buffer.com 且出现侧边栏（Community/Create 链接）
let ok = false;
for (let i = 0; i < 30; i++) {
  await page.waitForTimeout(3000);
  const url = page.url();
  const hasSidebar = await page.locator('a:has-text("Community"), a:has-text("Create")').count();
  const hasLogin = await page.locator('input[name=email]').count();
  if (hasSidebar > 0 && hasLogin === 0 && /publish\.buffer\.com/.test(url)) {
    ok = true;
    break;
  }
  if (i % 5 === 0) console.log(`等待登录... (${i * 3}s) url=${url.slice(0, 60)}`);
}
if (!ok) {
  console.error('登录未完成（可能密码错误或需要验证）');
  await browser.close();
  process.exit(1);
}

const state = await page.context().storageState();
writeFileSync(statePath, JSON.stringify(state, null, 2));
console.log(`登录成功，storageState 已保存 (${state.cookies.length} cookies)`);

// 验证目标频道可访问
await page.goto('https://publish.buffer.com/channels/6a202882c687a22dd45735b6/community/', { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(5000);
const restricted = await page.locator('text=Access restricted').count();
if (restricted > 0) {
  console.error('警告：登录成功但目标频道仍显示 Access restricted');
} else {
  console.log('目标频道可访问（无 Access restricted）');
}
await browser.close();
