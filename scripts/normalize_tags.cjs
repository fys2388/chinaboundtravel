/**
 * Normalize all Hugo post tags to PascalCase (no spaces, no kebab-case).
 * Creates TAG_NAMING_CONVENTION.md and updates all frontmatter.
 *
 * Tag naming rules:
 *   - PascalCase with no spaces: ChinaTravel, SichuanFood, TeaCulture
 *   - Multi-word concepts: HighSpeedRail, ChinaTravelTips
 *   - Geo tags: USToChina, EUToChina, AustraliaToChina
 *   - City/Region: Chengdu, Shanghai, Beijing, WesternSichuan
 *
 * Usage:
 *   node scripts/normalize_tags.cjs
 */

const fs = require('fs');
const path = require('path');

const REPO_PATH = path.resolve(__dirname, '..');
const POST_DIR = path.join(REPO_PATH, 'content', 'posts');
const SKIP_DIRS = new Set(['.archived', '.audit_backup', 'drafts']);

// Comprehensive tag mapping: old form -> PascalCase standard
const TAG_MAP = {
  // Geo-targeting tags (keep as-is, already PascalCase)
  'AustraliaToChina': 'AustraliaToChina',
  'USToChina': 'USToChina',
  'EuropeToChina': 'EuropeToChina',

  // Content type tags (standardize)
  'ChinaTravel': 'ChinaTravel',
  'China travel': 'ChinaTravel',
  'china travel': 'ChinaTravel',
  'TravelGuide': 'ChinaTravelGuide',
  'Travel Tips': 'ChinaTravelTips',
  'travel tips': 'ChinaTravelTips',
  'China Travel': 'ChinaTravel',
  'Travel guide': 'ChinaTravelGuide',
  '2026 Travel': 'ChinaTravel2026',
  'China road trip': 'ChinaRoadTrip',

  // Food tags
  'ChinaFood': 'ChinaFood',
  'China food': 'ChinaFood',

  // Tea
  'TeaCulture': 'TeaCulture',

  // City tags
  'Chengdu': 'Chengdu',
  'Shanghai': 'Shanghai',
  'Sichuan': 'Sichuan',
  'Sichuan travel': 'SichuanTravel',
  'Sichuan Guide': 'SichuanGuide',
  'western Sichuan': 'WesternSichuan',
  'Hunan Travel': 'HunanTravel',

  // Visa
  'Visa': 'ChinaVisa',
  'China Visa': 'ChinaVisa',
  'Transit': 'ChinaTransit',
  'Travel Policy': 'ChinaTravelPolicy',
  'News': 'ChinaTravelNews',

  // Internet/Payment
  'China VPN': 'ChinaVPN',
  'eSIM': 'ChinaESim',
  'Internet in China': 'ChinaInternet',
  'alipay': 'Alipay',
  'wechat pay': 'WeChatPay',
  'china payment': 'ChinaPayment',
  'foreigners in china': 'ForeignersInChina',

  // Adventure
  'camping in China': 'ChinaCamping',
  'overland adventure': 'OverlandAdventure',
  'Tibetan Plateau': 'TibetanPlateau',

  // Zhangjiajie specific
  'Zhangjiajie': 'Zhangjiajie',
  'Avatar Mountains China': 'AvatarMountainsChina',
  'Tianmen Mountain': 'TianmenMountain',
  'China National Parks': 'ChinaNationalParks',
  'China Hiking': 'ChinaHiking',
  'Zhangjiajie Itinerary': 'ZhangjiajieItinerary',
  'Yuanjiajie': 'Yuanjiajie',

  // Panda
  'Panda Base': 'ChengduPandaBase',

  // China general
  'China': 'China',
};

function normalizeTag(tag) {
  const trimmed = tag.trim();
  // Direct lookup
  if (TAG_MAP[trimmed]) return TAG_MAP[trimmed];
  // Case-insensitive lookup
  const lower = trimmed.toLowerCase();
  for (const [key, value] of Object.entries(TAG_MAP)) {
    if (key.toLowerCase() === lower) return value;
  }
  // Already PascalCase? Return as-is
  if (/^[A-Z][a-zA-Z]*$/.test(trimmed) && !trimmed.includes(' ')) return trimmed;
  // Convert "multi word tag" to "MultiWordTag"
  return trimmed.split(/[\s-_]+/).map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join('');
}

function parseAndNormalizeFrontmatter(content) {
  if (!content.startsWith('---')) return { content, changed: false };

  const parts = content.split('---');
  if (parts.length < 3) return { content, changed: false };

  let fm = parts[1];
  const body = parts.slice(2).join('---');
  let changed = false;

  // Normalize tags section
  fm = fm.replace(/^tags:\s*$/m, (match) => {
    // Tags header with no values on same line - find the list items
    return match; // Keep header, process items separately
  });

  // Process tag list items
  const lines = fm.split('\n');
  const newLines = [];
  let inTags = false;
  let processedTagValues = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.trim() === 'tags:') {
      inTags = true;
      newLines.push(line);
      continue;
    }

    if (inTags) {
      // Check if this line is a list item under tags
      if (line.match(/^\s+-\s+/)) {
        // Extract tag value
        const tagMatch = line.match(/^\s+-\s+["']?(.+?)["']?\s*$/);
        if (tagMatch) {
          const oldTag = tagMatch[1];
          const newTag = normalizeTag(oldTag);
          if (oldTag !== newTag) {
            newLines.push(`  - ${newTag}`);
            changed = true;
          } else {
            newLines.push(line);
          }
        } else {
          newLines.push(line);
        }
        continue;
      }
      // Check if tags is inline array: tags: [China, Travel]
      // Already handled by regex above
      // Non-list, non-empty line means we left the tags section
      if (line.trim() !== '' && !line.match(/^\s+-\s+/)) {
        inTags = false;
      }
    }

    newLines.push(line);
  }

  if (changed) {
    const newContent = '---\n' + newLines.join('\n') + '---' + body;
    return { content: newContent, changed: true };
  }

  return { content, changed: false };
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
  console.log('[Tags] Normalizing tags across all posts...');
  const postFiles = getPostFiles();
  console.log(`[Tags] Found ${postFiles.length} post files`);

  let totalChanged = 0;
  const allOldTags = new Set();
  const allNewTags = new Set();
  const changes = [];

  for (const postFile of postFiles) {
    try {
      const raw = fs.readFileSync(postFile, 'utf-8');
      const { content, changed } = parseAndNormalizeFrontmatter(raw);

      if (changed) {
        // Collect what changed
        const oldTags = [];
        const newTags = [];
        const oldFm = raw.split('---')[1] || '';
        const newFm = content.split('---')[1] || '';
        // Extract tags from both
        const tagRegex = /^\s+-\s+(.+?)\s*$/gm;
        let m;
        while ((m = tagRegex.exec(oldFm)) !== null) oldTags.push(m[1]);
        tagRegex.lastIndex = 0;
        while ((m = tagRegex.exec(newFm)) !== null) newTags.push(m[1]);

        fs.writeFileSync(postFile, content, 'utf-8');
        totalChanged++;
        const relPath = path.relative(REPO_PATH, postFile);
        changes.push({ file: relPath, oldTags, newTags });
        console.log(`  [*] ${relPath}`);
        for (let i = 0; i < oldTags.length; i++) {
          if (oldTags[i] !== newTags[i]) {
            console.log(`      ${oldTags[i]} -> ${newTags[i]}`);
            allOldTags.add(oldTags[i]);
            allNewTags.add(newTags[i]);
          }
        }
      }
    } catch (e) {
      console.error(`  [!] Error: ${path.basename(postFile)}: ${e.message}`);
    }
  }

  console.log(`\n[Tags] Changed ${totalChanged} files`);
  console.log(`[Tags] Total unique old tags: ${allOldTags.size}`);
  console.log(`[Tags] Total unique new tags: ${allNewTags.size}`);

  // Create TAG_NAMING_CONVENTION.md
  const convention = `# Tag Naming Convention

## Standard Format: PascalCase (no spaces)

All tags must use PascalCase with no spaces, no kebab-case, no quotes.

## Standardized Tags

| Tag | Used For |
|-----|----------|
| ChinaTravel | General China travel content |
| ChinaTravelGuide | Comprehensive guides |
| ChinaTravelTips | Practical tips and advice |
| ChinaFood | Food and dining |
| TeaCulture | Tea-related content |
| ChinaVisa | Visa and entry requirements |
| ChinaTransit | Transit and visa-free entry |
| ChinaTravelPolicy | Policy changes and updates |
| ChinaTravelNews | Travel news |
| ChinaVPN | VPN and internet access |
| ChinaESim | eSIM and connectivity |
| ChinaInternet | Internet-related guides |
| Alipay | Alipay payment |
| WeChatPay | WeChat Pay payment |
| ChinaPayment | General payment guides |
| ForeignersInChina | Expat and foreigner guides |
| Chengdu | Chengdu city content |
| Shanghai | Shanghai city content |
| Beijing | Beijing city content |
| Sichuan | Sichuan province |
| SichuanTravel | Sichuan travel guides |
| WesternSichuan | Western Sichuan region |
| HunanTravel | Hunan province travel |
| Zhangjiajie | Zhangjiajie park |
| TianmenMountain | Tianmen Mountain |
| AvatarMountainsChina | Avatar/Hallelujah Mountains |
| ChinaNationalParks | National parks |
| ChinaHiking | Hiking content |
| ZhangjiajieItinerary | Zhangjiajie itineraries |
| Yuanjiajie | Yuanjiajie scenic area |
| ChengduPandaBase | Panda Base |
| ChinaCamping | Camping in China |
| OverlandAdventure | Overland/adventure travel |
| TibetanPlateau | Tibetan Plateau region |
| ChinaRoadTrip | Road trip content |
| USToChina | Content targeting US travelers |
| EUToChina | Content targeting EU travelers |
| AustraliaToChina | Content targeting AU/NZ travelers |
| China | General China tag |
| ChinaTravel2026 | 2026-specific travel content |

## Rules

1. NO spaces in tags (wrong: "China Travel", right: "ChinaTravel")
2. NO kebab-case (wrong: "china-travel", right: "ChinaTravel")
3. NO lowercase-only tags (wrong: "chengdu", right: "Chengdu")
4. Multi-word tags use PascalCase (HighSpeedRail, GreatWall)
5. Geo tags use format: OriginToChina (USToChina, EUToChina, AustraliaToChina)
6. Maximum 6-8 tags per article
7. Always include at least one broad tag (ChinaTravel) and one specific tag (city/topic)
`;
  const conventionPath = path.join(REPO_PATH, 'TAG_NAMING_CONVENTION.md');
  fs.writeFileSync(conventionPath, convention, 'utf-8');
  console.log(`\n[Tags] Created TAG_NAMING_CONVENTION.md`);
  console.log(`[Tags] Done!`);
}

main();
