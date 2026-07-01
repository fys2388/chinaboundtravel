/**
 * Analyze internal links across all Hugo posts.
 * Outputs a report showing link counts and recommending links to add.
 */
const fs = require('fs');
const path = require('path');

const REPO_PATH = path.resolve(__dirname, '..');
const POST_DIR = path.join(REPO_PATH, 'content', 'posts');
const SKIP_DIRS = new Set(['.archived', '.audit_backup', 'drafts']);

function getPostFiles() {
  const files = [];
  if (!fs.existsSync(POST_DIR)) return files;
  function walk(dir) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        if (!SKIP_DIRS.has(entry.name)) walk(fullPath);
      } else if (entry.name.endsWith('.md')) {
        files.push(fullPath);
      }
    }
  }
  walk(POST_DIR);
  return files;
}

function parseFrontmatter(content) {
  if (!content.startsWith('---')) return {};
  const parts = content.split('---');
  if (parts.length < 3) return {};
  const fm = {};
  let listKey = '';
  for (const line of parts[1].trim().split('\n')) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    if (trimmed.startsWith('- ')) {
      const value = trimmed.slice(2).trim().replace(/^["']|["']$/g, '');
      if (listKey) { if (!fm[listKey]) fm[listKey] = []; fm[listKey].push(value); }
      continue;
    }
    if (trimmed.includes(':') && !trimmed.startsWith('-')) {
      const colonIdx = trimmed.indexOf(':');
      const key = trimmed.slice(0, colonIdx).trim();
      const value = trimmed.slice(colonIdx + 1).trim();
      if (value === '' || value === '[]') { listKey = key; fm[key] = []; }
      else { listKey = ''; fm[key] = value.replace(/^["']|["']$/g, ''); }
    }
  }
  return fm;
}

function extractLinks(content) {
  const internalLinks = [];
  const externalLinks = [];
  const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
  let m;
  while ((m = linkRegex.exec(content)) !== null) {
    const url = m[2];
    if (url.includes('chinaboundtravel.com/posts/')) {
      internalLinks.push({ text: m[1], url });
    } else if (url.startsWith('http')) {
      externalLinks.push({ text: m[1], url });
    }
  }
  return { internalLinks, externalLinks };
}

function main() {
  const postFiles = getPostFiles();
  const results = [];
  const slugToPost = {};

  for (const postFile of postFiles) {
    const raw = fs.readFileSync(postFile, 'utf-8');
    const fm = parseFrontmatter(raw);
    const title = fm.title || path.basename(postFile, '.md');
    const slug = fm.slug || path.basename(postFile, '.md');
    const tags = Array.isArray(fm.tags) ? fm.tags : [];

    let body = raw;
    if (raw.startsWith('---')) {
      const parts = raw.split('---');
      if (parts.length >= 3) body = parts.slice(2).join('---');
    }

    const { internalLinks, externalLinks } = extractLinks(body);
    const internalSlugs = [...new Set(internalLinks.map(l => {
      const match = l.url.match(/\/posts\/([^/]+)/);
      return match ? match[1] : null;
    }).filter(Boolean))];

    slugToPost[slug] = { title, tags, slug };
    results.push({ title, slug, tags, internalCount: internalLinks.length, uniqueSlugs: internalSlugs, externalCount: externalLinks.length });
  }

  // Sort by internal link count ascending
  results.sort((a, b) => a.internalCount - b.internalCount);

  console.log('='.repeat(70));
  console.log('INTERNAL LINK ANALYSIS');
  console.log('='.repeat(70));

  const lowLink = results.filter(r => r.internalCount <= 1);
  const medLink = results.filter(r => r.internalCount > 1 && r.internalCount < 4);
  const goodLink = results.filter(r => r.internalCount >= 4);

  console.log(`\nLow (0-1 links): ${lowLink.length} articles`);
  console.log(`Medium (2-3 links): ${medLink.length} articles`);
  console.log(`Good (4+ links): ${goodLink.length} articles`);

  console.log('\n--- Articles needing internal links ---');
  for (const r of lowLink) {
    console.log(`\n[${r.slug}] "${r.title}" (${r.internalCount} internal links)`);
    console.log(`  Tags: ${r.tags.join(', ')}`);
    // Find related articles
    const related = results.filter(other =>
      other.slug !== r.slug &&
      other.internalCount >= 2 &&
      (other.tags.some(t => r.tags.includes(t)) || other.uniqueSlugs.length >= 2)
    ).slice(0, 5);
    if (related.length > 0) {
      console.log(`  Recommended links to add:`);
      for (const rec of related) {
        console.log(`    - [${rec.title}](https://chinaboundtravel.com/posts/${rec.slug}/)`);
      }
    }
  }

  console.log('\n--- Medium link articles ---');
  for (const r of medLink) {
    console.log(`[${r.slug}] "${r.title}" (${r.internalCount} links)`);
  }
  console.log('\n--- Good link articles ---');
  for (const r of goodLink) {
    console.log(`[${r.slug}] "${r.title}" (${r.internalCount} links)`);
  }
}

main();
