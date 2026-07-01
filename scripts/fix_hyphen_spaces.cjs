/**
 * fix_hyphen_spaces.cjs
 *
 * Batch-fix AI-generated "space - hyphen - space" errors in markdown posts.
 *
 * Strategy: Replace "word - word" with "word-word" only when it looks like
 * a genuine hyphenated compound, NOT a sentence-level dash.
 *
 * Rules:
 *   1. Skip if either word contains digits (date ranges)
 *   2. Skip if inside Hugo shortcodes {{< ... >}}
 *   3. Skip if inside markdown image alt text ![...](...)
 *   4. Skip if BOTH words start with uppercase AND right word is a function word
 *      (article/pronoun) -> title/subtitle separator like "China - The Complete Guide"
 *   5. If preceded by "lowercase + space" (mid-sentence):
 *      a. Skip if right word is a sentence-starter (pronoun, article, verb)
 *      b. Allow if left word is a known compound prefix OR right word is a known
 *         compound suffix, AND the other side is also a compound element or small word
 *   6. If preceded by non-lowercase (start of line, punctuation, uppercase) -> allow
 *   7. Chain processing handles multi-word compounds like "hole - in - the - wall"
 */

const fs = require('fs');
const path = require('path');

const POSTS_DIR = path.resolve(__dirname, '..', 'content', 'posts');

// Words commonly appearing as the RIGHT part of hyphenated compounds
const RIGHT_COMPOUND_PARTS = new Set([
  'eyed', 'fried', 'known', 'try', 'visit', 'pull', 'class', 'quality',
  'term', 'time', 'hand', 'made', 'found', 'changing', 'inspiring',
  'flowing', 'breaking', 'friendly', 'effective', 'winning', 'style',
  'cake', 'depth', 'plus', 'up', 'boggling', 'watering', 'serving',
  'centric', 'focused', 'oriented', 'driven', 'based', 'related',
  'free', 'powered', 'saving', 'packed', 'built', 'selected',
  'crafted', 'curated', 'tested', 'approved', 'rated', 'reviewed',
  'tier', 'level', 'speed', 'end', 'side', 'line', 'class',
  'grade', 'scale', 'stop', 'round', 'way', 'star', 'piece',
]);

// Words commonly appearing as the LEFT part of hyphenated compounds
// (Excludes words too common in sentence contexts: real, up, over, under, out, off, on, by)
const LEFT_COMPOUND_PARTS = new Set([
  'well', 'must', 'high', 'long', 'short', 'full', 'part', 'hard',
  'ever', 'awe', 'free', 'record', 'cost', 'budget', 'family', 'world',
  'mouth', 'no', 'in', 'step', 'mind', 'first', 'brand', 'top',
  'best', 'hand', 'new', 'home', 'self', 'all', 'cross', 'multi',
  'mini', 'eco', 'pro', 'anti', 'semi', 'co', 'ex', 'pre', 're',
  'sub', 'super', 'macro', 'micro', 'nano', 'extra', 'hyper', 'mega',
  'ultra', 'stir', 'wide', 'open', 'deep', 'quick', 'slow', 'fast', 'easy',
  'safe', 'clean', 'clear', 'close', 'cold', 'cool', 'dark', 'dry',
  'fair', 'fine', 'flat', 'fresh', 'good', 'great', 'half',
  'heavy', 'hot', 'key', 'large', 'late', 'lead', 'light', 'live',
  'loud', 'low', 'main', 'near', 'odd', 'only', 'own', 'past',
  'plain', 'prime', 'proper', 'proud', 'raw', 'rich',
  'rough', 'round', 'sharp', 'sheer', 'short', 'sight', 'single',
  'smooth', 'soft', 'sole', 'solid', 'sound', 'south', 'space',
  'square', 'still', 'straight', 'sure', 'sweet', 'thick', 'thin',
  'tight', 'tiny', 'tough', 'true', 'warm', 'weak', 'wet', 'wild',
  'wise', 'worth',
]);

// Small functional words that can appear inside multi-word compounds
// e.g., "hole-in-the-wall", "day-to-day", "step-by-step", "in-depth"
const COMPOUND_SMALL_WORDS = new Set([
  'in', 'the', 'a', 'to', 'and', 'of', 'or', 'an', 'at', 'by', 'for', 'on',
]);

// Words that commonly START a new clause/sentence after a dash
// If the right word matches these, it's likely a sentence dash, not a compound
const SENTENCE_STARTERS = new Set([
  'this', 'that', 'these', 'those', 'here', 'there',
  'we', 'they', 'you', 'it', 'he', 'she', 'i',
  'is', 'was', 'are', 'were', 'will', 'would', 'could', 'should', 'can', 'may',
  'not', 'just', 'even', 'still', 'never', 'always', 'now', 'then',
  'but', 'yet', 'so',
  'my', 'our', 'your', 'his', 'her', 'its', 'their',
  'if', 'when', 'while', 'after', 'before', 'since', 'until', 'because',
  'a', 'an', 'the', 'every',
  'tomorrow', 'today', 'yesterday', 'nevertheless', 'however', 'meanwhile',
]);

// Function words used in titles/subtitles after a dash separator
const TITLE_FUNCTION_WORDS = new Set([
  'A', 'An', 'The', 'This', 'That', 'These', 'Those',
  'Our', 'My', 'Your', 'His', 'Her', 'Its',
]);

function isInsideShortcode(line, index) {
  const before = line.substring(0, index);
  const open = before.lastIndexOf('{{<');
  const close = before.lastIndexOf('>}}');
  return open > close;
}

function isInsideImageAlt(line, matchStart) {
  const imgAltStart = line.indexOf('![');
  const imgAltEnd = line.indexOf('](');
  if (imgAltStart === -1 || imgAltEnd === -1) return false;
  return matchStart > imgAltStart && matchStart < imgAltEnd;
}

function shouldReplace(line, matchStart, left, right) {
  // Skip digits
  if (/\d/.test(left) || /\d/.test(right)) return false;

  // Skip Hugo shortcodes
  if (isInsideShortcode(line, matchStart)) return false;

  // Skip markdown image alt text
  if (isInsideImageAlt(line, matchStart)) return false;

  const leftLower = left.toLowerCase();
  const rightLower = right.toLowerCase();

  // Rule 4: If BOTH words start with uppercase AND right is a title function word,
  // this is likely a subtitle separator ("China - The Complete Guide")
  if (/^[A-Z]/.test(left) && /^[A-Z]/.test(right) && TITLE_FUNCTION_WORDS.has(right)) {
    return false;
  }

  // Check preceding context for mid-sentence detection
  if (matchStart > 0) {
    const charBefore = line[matchStart - 1];

    // If directly preceded by hyphen (from a previous compound fix), allow
    if (charBefore === '-') return true;

    // If directly preceded by a lowercase letter, skip
    if (/[a-z]/.test(charBefore)) return false;

    // If preceded by space, check one more character back
    if (charBefore === ' ' && matchStart >= 2) {
      const charBeforeBefore = line[matchStart - 2];

      if (/[a-z]/.test(charBeforeBefore)) {
        // Preceded by "lowercase + space" -> likely mid-sentence

        // Rule 5a: Skip if right word is a sentence-starter
        if (SENTENCE_STARTERS.has(rightLower)) return false;

        // Rule 5b: Allow if BOTH sides are recognized compound elements
        const leftIsCompound = LEFT_COMPOUND_PARTS.has(leftLower) || RIGHT_COMPOUND_PARTS.has(leftLower) || COMPOUND_SMALL_WORDS.has(leftLower);
        const rightIsCompound = LEFT_COMPOUND_PARTS.has(rightLower) || RIGHT_COMPOUND_PARTS.has(rightLower) || COMPOUND_SMALL_WORDS.has(rightLower);

        if (leftIsCompound && rightIsCompound) {
          return true;
        }

        // Single-side match is not enough when mid-sentence
        return false;
      }
    }
  }

  // Rule 6: At start of line, after punctuation, after uppercase -> allow
  return true;
}

function processFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf-8');
  const lines = content.split('\n');
  const replacements = [];

  for (let i = 0; i < lines.length; i++) {
    const lineNum = i + 1;
    let line = lines[i];
    let changed = true;
    let passCount = 0;

    while (changed) {
      changed = false;
      passCount++;
      if (passCount > 20) break;

      const regex = /([a-zA-Z]+)\s+-\s+([a-zA-Z]+)/g;
      let match;

      while ((match = regex.exec(line)) !== null) {
        const fullMatch = match[0];
        const left = match[1];
        const right = match[2];
        const matchStart = match.index;

        if (shouldReplace(line, matchStart, left, right)) {
          const replacement = `${left}-${right}`;
          replacements.push({
            line: lineNum,
            before: fullMatch,
            after: replacement,
          });

          line = line.replace(fullMatch, replacement);
          changed = true;
          break;
        }
      }
    }

    if (replacements.some((r) => r.line === lineNum)) {
      lines[i] = line;
    }
  }

  if (replacements.length > 0) {
    fs.writeFileSync(filePath, lines.join('\n'), 'utf-8');
  }

  return replacements;
}

function main() {
  const entries = fs.readdirSync(POSTS_DIR, { withFileTypes: true });
  const files = entries
    .filter((e) => e.isFile() && e.name.endsWith('.md'))
    .map((e) => path.join(POSTS_DIR, e.name));

  let totalReplacements = 0;
  const allReplacements = [];

  console.log(`\nScanning ${files.length} markdown files in ${POSTS_DIR}\n`);
  console.log('='.repeat(72));

  for (const filePath of files) {
    const replacements = processFile(filePath);

    if (replacements.length > 0) {
      const shortName = path.basename(filePath);
      console.log(`\n[${shortName}] - ${replacements.length} replacement(s):`);
      for (const r of replacements) {
        console.log(`  Line ${r.line}: "${r.before}" -> "${r.after}"`);
        allReplacements.push({ file: shortName, ...r });
      }
      totalReplacements += replacements.length;
    }
  }

  console.log('\n' + '='.repeat(72));
  console.log(`\n=== SUMMARY ===`);
  console.log(`  Files processed: ${files.length}`);
  console.log(`  Files changed:   ${new Set(allReplacements.map((r) => r.file)).size}`);
  console.log(`  Total replacements: ${totalReplacements}`);

  if (allReplacements.length > 0) {
    console.log(`\n=== ALL REPLACEMENTS (${allReplacements.length}) ===`);
    for (const r of allReplacements) {
      console.log(`  ${r.file}:${r.line} "${r.before}" -> "${r.after}"`);
    }
  } else {
    console.log(`\nNo replacements needed.`);
  }
}

main();
