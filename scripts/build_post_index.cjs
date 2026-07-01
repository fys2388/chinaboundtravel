/**
 * Build a post index JSON from Hugo content/posts directory.
 * This index is injected into Joran's content generation prompt for accurate internal links.
 *
 * Usage:
 *   node scripts/build_post_index.cjs
 */

const fs = require('fs');
const path = require('path');

const REPO_PATH = path.resolve(__dirname, '..');
const POST_DIR = path.join(REPO_PATH, 'content', 'posts');
const OUTPUT_PATH = path.join(REPO_PATH, 'config', 'post_index.json');
const SKIP_DIRS = new Set(['.archived', '.audit_backup', 'drafts']);

function parseFrontmatter(content) {
  if (!content.startsWith('---')) return {};
  const parts = content.split('---');
  if (parts.length < 3) return {};
  const fm = {};
  let inList = false;
  let listKey = '';
  for (const line of parts[1].trim().split('\n')) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    if (trimmed.startsWith('#')) continue;

    // List item (starts with -)
    if (trimmed.startsWith('- ')) {
      const value = trimmed.slice(2).trim().replace(/^["']|["']$/g, '');
      if (listKey) {
        if (!fm[listKey]) fm[listKey] = [];
        fm[listKey].push(value);
      }
      continue;
    }

    // Check if this is a key with list values on subsequent lines
    if (trimmed.includes(':') && !trimmed.startsWith('-')) {
      const colonIdx = trimmed.indexOf(':');
      const key = trimmed.slice(0, colonIdx).trim();
      const value = trimmed.slice(colonIdx + 1).trim();

      if (value === '' || value === '[]') {
        listKey = key;
        fm[key] = [];
        continue;
      } else {
        listKey = '';
        fm[key] = value.replace(/^["']|["']$/g, '');
      }
    }
  }
  return fm;
}

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

function main() {
  console.log('[Index] Building post index from:', POST_DIR);
  const postFiles = getPostFiles();
  console.log(`[Index] Found ${postFiles.length} post files`);

  const posts = [];
  for (const postFile of postFiles) {
    try {
      const raw = fs.readFileSync(postFile, 'utf-8');
      if (raw.length < 200) continue;

      const fm = parseFrontmatter(raw);
      const title = fm.title || path.basename(postFile, '.md');
      const slug = fm.slug || path.basename(postFile, '.md');
      const tags = Array.isArray(fm.tags) ? fm.tags : [];
      const categories = Array.isArray(fm.categories) ? fm.categories : [];
      const geo = fm.geo || 'US';
      const draft = fm.draft === 'true' || fm.draft === true;
      const date = fm.date || '';

      if (draft) continue;

      posts.push({
        title,
        slug,
        tags,
        categories,
        geo,
        date,
        url: `https://chinaboundtravel.com/posts/${slug}/`
      });

    } catch (e) {
      console.error(`  [!] Error: ${path.basename(postFile)}: ${e.message}`);
    }
  }

  // Sort by date descending
  posts.sort((a, b) => (b.date || '').localeCompare(a.date || ''));

  const index = {
    generated_at: new Date().toISOString(),
    total_posts: posts.length,
    base_url: 'https://chinaboundtravel.com',
    posts
  };

  fs.writeFileSync(OUTPUT_PATH, JSON.stringify(index, null, 2), 'utf-8');
  console.log(`[Index] Written ${posts.length} posts to: config/post_index.json`);

  // Print summary
  console.log('\n[Index] Posts by geo:');
  const geoCounts = {};
  for (const p of posts) {
    geoCounts[p.geo] = (geoCounts[p.geo] || 0) + 1;
  }
  for (const [geo, count] of Object.entries(geoCounts).sort((a, b) => b[1] - a[1])) {
    console.log(`  ${geo}: ${count} posts`);
  }

  // All tags
  const allTags = new Set();
  for (const p of posts) {
    p.tags.forEach(t => allTags.add(t));
  }
  console.log(`\n[Index] Total unique tags: ${allTags.size}`);
  console.log(`[Index] Tags: ${[...allTags].sort().join(', ')}`);
}

main();
