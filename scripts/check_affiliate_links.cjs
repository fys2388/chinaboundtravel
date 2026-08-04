const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');
const { URL } = require('url');

const ROOT = path.normalize('E:/AI/dulizhan/travel-blog');
const POSTS_DIR = path.join(ROOT, 'content', 'posts');

function walk(dir, ext, ignore = []) {
  const results = [];
  if (!fs.existsSync(dir)) return results;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (ignore.some(i => full.includes(i))) continue;
      results.push(...walk(full, ext, ignore));
    } else if (entry.isFile() && entry.name.endsWith(ext)) {
      results.push(full);
    }
  }
  return results;
}

const AFFILIATE_PATTERNS = [
  /safetywing\.com/i,
  /airalo\.com/i,
  /hotellook\.com/i,
  /klook\./i,
  /affiliatescn\.net/i,
  /emrldtp\.com/i,
  /travelpayouts/i,
  /impact\.com/i,
  /commissionjunction/i,
  /cj\.com/i,
  /booking\.com/i,
  /trip\.com/i,
  /expressvpn\.com/i,
  /nordvpn\.com/i,
  /surfshark\.com/i,
];

function extractUrls(text) {
  const urls = new Set();
  const mdRe = /!?\[[^\]]*\]\(([^)\s]+)\)/g;
  const htmlRe = /<a[^>]+href=["']([^"']+)["']/g;
  let m;
  while ((m = mdRe.exec(text))) urls.add(m[1].trim());
  while ((m = htmlRe.exec(text))) urls.add(m[1].trim());
  return Array.from(urls).filter(u => AFFILIATE_PATTERNS.some(p => p.test(u)));
}

function checkUrl(url) {
  return new Promise((resolve) => {
    const parsed = new URL(url);
    const client = parsed.protocol === 'https:' ? https : http;
    const req = client.request(parsed, { method: 'HEAD', timeout: 15000 }, (res) => {
      const status = res.statusCode;
      if (status >= 300 && status < 400 && res.headers.location) {
        const redirectUrl = new URL(res.headers.location, url).toString();
        checkUrl(redirectUrl).then(r => resolve({ ...r, originalUrl: url }));
        return;
      }
      if (status === 405) {
        checkUrl(url, 'GET').then(r => resolve({ ...r, originalUrl: url }));
        return;
      }
      resolve({ url, status, ok: status >= 200 && status < 400, method: 'HEAD' });
    });
    req.on('error', (err) => resolve({ url, status: 'ERROR', ok: false, error: err.message }));
    req.on('timeout', () => { req.destroy(); resolve({ url, status: 'TIMEOUT', ok: false }); });
    req.end();
  });
}

function checkUrlGet(url) {
  return new Promise((resolve) => {
    const parsed = new URL(url);
    const client = parsed.protocol === 'https:' ? https : http;
    const req = client.request(parsed, { method: 'GET', timeout: 20000 }, (res) => {
      const status = res.statusCode;
      res.resume();
      if (status >= 300 && status < 400 && res.headers.location) {
        const redirectUrl = new URL(res.headers.location, url).toString();
        checkUrlGet(redirectUrl).then(r => resolve({ ...r, originalUrl: url }));
        return;
      }
      resolve({ url, status, ok: status >= 200 && status < 400, method: 'GET' });
    });
    req.on('error', (err) => resolve({ url, status: 'ERROR', ok: false, error: err.message }));
    req.on('timeout', () => { req.destroy(); resolve({ url, status: 'TIMEOUT', ok: false }); });
    req.end();
  });
}

async function main() {
  const files = walk(POSTS_DIR, '.md', ['.archived', '.audit_backup', 'drafts', '_draft']);
  const fileMap = {};
  for (const f of files) {
    const text = fs.readFileSync(f, 'utf-8');
    const urls = extractUrls(text);
    if (urls.length) fileMap[f] = urls;
  }

  const allUrls = new Set();
  Object.values(fileMap).forEach(urls => urls.forEach(u => allUrls.add(u)));

  console.log(`Scanning ${Object.keys(fileMap).length} posts, ${allUrls.size} unique affiliate URLs...\n`);

  const results = [];
  for (const url of allUrls) {
    let r = await checkUrl(url);
    // Retry with GET if HEAD fails for non-200/ok
    if (!r.ok && r.status !== 'TIMEOUT' && r.status !== 'ERROR') {
      const getR = await checkUrlGet(url);
      if (getR.ok) r = getR;
    }
    results.push(r);
  }

  const broken = results.filter(r => !r.ok);
  const byFile = [];
  for (const [f, urls] of Object.entries(fileMap)) {
    const bad = urls.filter(u => broken.some(b => b.url === u || b.originalUrl === u));
    if (bad.length) byFile.push({ file: path.basename(f), bad });
  }

  if (broken.length) {
    console.log(`[FAIL] ${broken.length} affiliate URL(s) unavailable or returned error:\n`);
    for (const b of broken) {
      console.log(`  ${b.status} ${b.url}${b.originalUrl && b.originalUrl !== b.url ? ' (redirect from ' + b.originalUrl + ')' : ''}${b.error ? ' (' + b.error + ')' : ''}`);
    }
    console.log('\nBy file:');
    for (const item of byFile) {
      console.log(`  ${item.file}:`);
      item.bad.forEach(u => console.log(`    - ${u}`));
    }
  } else {
    console.log('[PASS] All affiliate URLs returned 2xx.');
  }

  console.log(`\n--- Summary ---`);
  console.log(`  Total affiliate URLs checked: ${results.length}`);
  console.log(`  OK: ${results.filter(r => r.ok).length}`);
  console.log(`  Broken: ${broken.length}`);

  process.exit(broken.length ? 1 : 0);
}

main();
