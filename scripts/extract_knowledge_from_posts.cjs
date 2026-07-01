/**
 * Extract knowledge from existing Hugo blog posts into the content knowledge base.
 * Populates config/content_knowledge_base.json with real information from published articles.
 *
 * Usage:
 *   node scripts/extract_knowledge_from_posts.cjs
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const REPO_PATH = path.resolve(__dirname, '..');
const POST_DIR = path.join(REPO_PATH, 'content', 'posts');
const KB_PATH = path.join(REPO_PATH, 'config', 'content_knowledge_base.json');
const SKIP_DIRS = new Set(['.archived', '.audit_backup', 'drafts']);

const CATEGORY_KEYWORDS = {
  destinations: ['attraction', 'mountain', 'park', 'lake', 'temple', 'wall', 'city guide',
    'must see', 'scenic', 'landmark', 'ancient city', 'viewpoint', 'cave', 'bridge'],
  transportation: ['high speed rail', 'hsr', 'metro', 'subway', 'train station', 'flight',
    'airport', 'bus', 'taxi', 'transport', 'drive', 'ride', 'ticket booking', 'rail', 'booking'],
  accommodation: ['hotel', 'hostel', 'stay', 'lodging', 'accommodation', 'airbnb', 'inn', 'sleep'],
  food: ['food', 'cuisine', 'hotpot', 'restaurant', 'street food', 'dumpling', 'noodle',
    'tea', 'tea culture', 'delivery', 'meituan', 'eleme', 'dining', 'drink', 'peppercorn', 'spicy', 'culinary'],
  culture: ['culture', 'history', 'traditional', 'festival', 'custom', 'ceremony',
    'heritage', 'dynasty', 'ancient', 'religion', 'art', 'confucian', 'taoism', 'buddhism', 'tradition'],
  tips: ['guide', 'tip', 'advice', 'warning', 'avoid', 'best practice', 'hack',
    'survive', 'mistake', 'lesson', 'recommendation', 'practical'],
  seasons: ['season', 'best time', 'weather', 'climate', 'spring', 'summer', 'winter', 'autumn', 'rainy', 'temperature'],
  budget: ['budget', 'cost', 'price', 'save', 'affordable', 'cheap', 'expensive',
    'free', 'ticket price', 'fee', 'money', 'currency', 'rmb', 'yuan', 'how much'],
  safety: ['safety', 'safe', 'danger', 'caution', 'scam', 'secure', 'emergency', 'police', 'insurance'],
  visa: ['visa', 'entry', 'customs', 'immigration', 'passport', 'transit', '144-hour', 'visa-free', 'visa free', 'permit', 'border']
};

function loadKB() {
  if (fs.existsSync(KB_PATH)) {
    return JSON.parse(fs.readFileSync(KB_PATH, 'utf-8'));
  }
  return {
    version: '1.0',
    last_updated: new Date().toISOString(),
    total_entries: 0,
    sources: ['xiaohongshu', 'douyin', 'zhihu', 'mafengwo', 'ctrip', 'weibo', 'blog'],
    knowledge_categories: {
      destinations: [], transportation: [], accommodation: [], food: [], culture: [],
      tips: [], seasons: [], budget: [], safety: [], visa: []
    },
    learning_metrics: { total_learned: 0, total_deduplicated: 0, total_filtered: 0, last_learning_date: '' }
  };
}

function saveKB(kb) {
  kb.version = '1.1';
  kb.last_updated = new Date().toISOString();
  kb.learning_metrics.last_learning_date = new Date().toISOString().split('T')[0];
  fs.writeFileSync(KB_PATH, JSON.stringify(kb, null, 2), 'utf-8');
}

function generateHash(content) {
  return crypto.createHash('md5').update(content).digest('hex');
}

function isDuplicate(hash, kb) {
  for (const cat of Object.values(kb.knowledge_categories)) {
    if (cat.some(e => e.hash === hash)) return true;
  }
  return false;
}

function classify(title, content) {
  const text = (title + ' ' + content).toLowerCase();
  let bestCat = 'tips', bestScore = 0;
  for (const [cat, keywords] of Object.entries(CATEGORY_KEYWORDS)) {
    const score = keywords.reduce((s, kw) => s + (text.includes(kw) ? 1 : 0), 0);
    if (score > bestScore) { bestScore = score; bestCat = cat; }
  }
  return bestCat;
}

function extractKeyPoints(title, content, slug) {
  const points = [];
  const seen = new Set();

  const addPoint = (p) => {
    const clean = p.replace(/\*+/g, '').trim();
    const lower = clean.toLowerCase();
    if (clean.length > 15 && clean.length < 120 && !seen.has(lower)) {
      seen.add(lower);
      points.push(clean);
    }
  };

  // H2 headings
  for (const m of content.matchAll(/^##\s+(.+)$/gm)) {
    addPoint('Section: ' + m[1]);
  }

  // Numbered/bulleted tips
  for (const pattern of [/^\d+\.\s+(.{20,120})$/gm, /^[-*]\s+(.{20,120})$/gm, /^\s+\d+\.\s+(.{20,120})$/gm]) {
    for (const m of content.matchAll(pattern)) addPoint(m[1]);
  }

  // Practical info
  for (const pattern of [/\$?\d+\s*(?:RMB|USD|yuan|CNY)?[\w\s]{5,50}/gi,
    /(?:open|opens?|hours?)\s*(?:from|:)\s*.{10,60}/gi,
    /(?:cost|price|fee|ticket)\s*(?:is|:)\s*.{10,60}/gi,
    /(?:best time|recommended)\s*(?:to|:)\s*.{10,60}/gi]) {
    for (const m of content.matchAll(pattern)) {
      const clean = m[0].trim();
      if (clean.length > 10 && clean.length < 80) addPoint('Practical: ' + clean);
    }
  }

  // Specific places for known articles
  if (slug.includes('zhangjiajie')) {
    ['Yuanjiajie', 'Tianzi Mountain', 'Golden Whip Stream', 'Tianmen Mountain', 'Tianmen Cave', 'Glass Skywalk', 'Huangshi Village'].forEach(place => {
      if (content.toLowerCase().includes(place.toLowerCase())) addPoint('Place: ' + place);
    });
  }
  if (slug.includes('xian') || slug.includes('terracotta')) {
    ['Terracotta Warriors', 'Pit 1', 'Pit 2', 'Pit 3', 'Bronze Chariots', 'Mount Li'].forEach(place => {
      if (content.toLowerCase().includes(place.toLowerCase())) addPoint('Place: ' + place);
    });
  }
  if (slug.includes('great-wall')) {
    ['Mutianyu', 'Jinshanling', 'Simatai', 'Badaling', 'Jiankou'].forEach(place => {
      if (content.toLowerCase().includes(place.toLowerCase())) addPoint('Place: ' + place);
    });
  }

  return points.slice(0, 10);
}

function extractSummary(title, content) {
  const paragraphs = content.split(/\n\s*\n/);
  const parts = [];
  for (const p of paragraphs) {
    const trimmed = p.trim();
    if (!trimmed || /^[#\[\|!]/.test(trimmed) || trimmed.length < 30) continue;
    let clean = trimmed.replace(/\*+/g, '').replace(/\[.*?\]\(.*?\)/g, '').trim();
    if (clean) parts.push(clean);
  }
  const summary = parts.slice(0, 5).join(' ');
  return summary.length > 500 ? summary.slice(0, 500) + '...' : summary;
}

function parseFrontmatter(content) {
  if (!content.startsWith('---')) return {};
  const parts = content.split('---');
  if (parts.length < 3) return {};
  const fm = {};
  for (const line of parts[1].trim().split('\n')) {
    const trimmed = line.trim();
    if (trimmed.includes(':') && !trimmed.startsWith('-')) {
      const [key, ...rest] = trimmed.split(':');
      fm[key.trim()] = rest.join(':').trim().replace(/^["']|["']$/g, '');
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
  return files.sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
}

function main() {
  console.log('[Extract] Scanning posts from:', POST_DIR);
  const kb = loadKB();
  const postFiles = getPostFiles();
  console.log(`[Extract] Found ${postFiles.length} post files`);

  const stats = { totalScanned: 0, totalExtracted: 0, totalDuplicates: 0, totalFiltered: 0, categoryCounts: {} };

  for (const postFile of postFiles) {
    try {
      const raw = fs.readFileSync(postFile, 'utf-8');
      if (raw.length < 200) { stats.totalFiltered++; continue; }

      const fm = parseFrontmatter(raw);
      const title = fm.title || path.basename(postFile, '.md');
      const slug = fm.slug || path.basename(postFile, '.md');
      const tags = fm.tags || [];

      let body = raw;
      if (raw.startsWith('---')) {
        const parts = raw.split('---');
        if (parts.length >= 3) body = parts.slice(2).join('---');
      }

      stats.totalScanned++;
      const category = classify(title, body);
      const keyPoints = extractKeyPoints(title, body, slug);
      if (keyPoints.length < 2) { stats.totalFiltered++; continue; }

      const summary = extractSummary(title, body);
      const hash = generateHash(title + summary.slice(0, 200));

      if (isDuplicate(hash, kb)) { stats.totalDuplicates++; continue; }

      const entry = {
        hash,
        source: 'blog_post',
        url: `https://chinaboundtravel.com/posts/${slug}/`,
        keyword: title,
        slug,
        tags: Array.isArray(tags) ? tags : [tags],
        category,
        content: summary,
        key_points: keyPoints,
        language: 'en',
        learned_at: new Date().toISOString(),
        relevance: keyPoints.length
      };

      kb.knowledge_categories[category].push(entry);
      kb.total_entries++;
      stats.totalExtracted++;
      stats.categoryCounts[category] = (stats.categoryCounts[category] || 0) + 1;

      console.log(`  [+] ${title.slice(0, 55)}... -> ${category} (${keyPoints.length} key_points)`);
    } catch (e) {
      console.error(`  [!] Error processing ${path.basename(postFile)}: ${e.message}`);
    }
  }

  kb.learning_metrics.total_learned += stats.totalExtracted;
  kb.learning_metrics.total_deduplicated += stats.totalDuplicates;
  kb.learning_metrics.total_filtered += stats.totalFiltered;
  saveKB(kb);

  console.log('\n' + '='.repeat(60));
  console.log('KNOWLEDGE EXTRACTION SUMMARY');
  console.log('='.repeat(60));
  console.log(`Posts scanned:          ${stats.totalScanned}`);
  console.log(`Knowledge extracted:    ${stats.totalExtracted}`);
  console.log(`Duplicates skipped:      ${stats.totalDuplicates}`);
  console.log(`Filtered (low quality):  ${stats.totalFiltered}`);
  console.log(`\nTotal KB entries:       ${kb.total_entries}`);
  console.log('\nBy category:');
  for (const [cat, count] of Object.entries(stats.categoryCounts).sort((a, b) => b[1] - a[1])) {
    console.log(`  ${cat.padEnd(18)}: +${count} (total: ${kb.knowledge_categories[cat].length})`);
  }
  console.log('='.repeat(60));
}

main();
