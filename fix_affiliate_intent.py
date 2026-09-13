#!/usr/bin/env python3
"""P0-5: Fix affiliate intent mismatching across all posts."""
import re
import os

POSTS_DIR = r"E:\AI\dulizhan\travel-blog\content\posts"

# Config: filename -> fix instructions
# remove_blocks: affiliate block types to remove (e.g. "hotel" removes {{< affiliate-hotel >}})
# remove_table_types: table rows containing these affiliate types to remove
# remove_inline: inline link shortcode names to remove entirely (booking-link, klook-link, etc.)
# remove_callouts_containing: remove entire > callout lines containing these shortcodes
# add_blocks: affiliate block types to add (inserted after last remaining block CTA)
# mid_cta_fix: {old_partner: new_partner} for affiliate-mid-cta
# remove_affiliate_link_keys: remove table rows with affiliate-link key=X

FIXES = {
    # === VISA / VISA-FREE ===
    "144-hour-visa-free-transit-guide.md": {
        "remove_blocks": ["hotel", "tour"],
        "remove_table_types": ["hotel", "tour"],
        "add_blocks": ["esim"],
        "mid_cta_fix": {"hotel": "esim"},
    },
    "2026-06-02-ultimate-guide-to-china-visa-for-tourists.md": {
        "remove_blocks": ["hotel", "tour"],
        "remove_table_types": ["hotel", "tour"],
        "add_blocks": ["esim"],
    },
    "china-extends-144-hour-visa-free-transit-policy-to-more-countries.md": {
        "remove_blocks": ["hotel", "tour"],
        "remove_table_types": ["hotel", "tour"],
    },
    "2026-09-08-china-visa-free-entry-2026-complete-guide-countries-rules-tips.md": {
        "remove_blocks": ["hotel", "tour"],
        "remove_table_types": ["hotel", "tour"],
    },

    # === PAYMENT (WeChat/Alipay) ===
    "2026-05-22-how-to-use-wechat-pay-as-a-foreigner.md": {
        "remove_blocks": ["flight", "tour"],
        "remove_table_types": ["flight", "tour"],
        "remove_inline": ["booking-link", "klook-link"],
        "remove_callouts_containing": ["booking-link", "klook-link"],
    },
    "2026-05-29-paypal-alipay-wechat-pay-qr-code-support.md": {
        "remove_blocks": ["hotel", "flight", "tour"],
        "remove_table_types": ["hotel", "flight", "tour"],
        "add_blocks": ["insurance"],
    },
    "2026-07-02-how-to-use-alipay-as-a-foreigner-complete-setup-guide-2026-guide.md": {
        "remove_blocks": ["hotel", "flight", "tour"],
        "remove_table_types": ["hotel", "flight", "tour"],
    },
    "2026-07-02-wechat-pay-for-foreigners-step-by-step-setup-and-common-mistakes-to-avoid-guide.md": {
        "remove_blocks": ["hotel", "flight", "tour"],
        "remove_table_types": ["hotel", "flight", "tour"],
    },
    "2026-09-08-alipay-vs-wechat-pay-which-tourists-should-use-china-2026.md": {
        "remove_blocks": ["hotel", "flight", "tour"],
        "remove_table_types": ["hotel", "flight", "tour"],
    },
    "alipay-wechat-pay-foreigners-guide.md": {
        "remove_blocks": ["hotel", "flight", "tour"],
        "remove_table_types": ["hotel", "flight", "tour"],
    },

    # === TRANSPORTATION / HIGH-SPEED RAIL ===
    "2026-05-25-china-high-speed-rail-how-to-book-tickets.md": {
        "remove_blocks": ["flight", "tour"],
        "remove_table_types": ["flight", "tour"],
    },
    "2026-05-27-how-to-survive-chinese-train-station.md": {
        "remove_blocks": ["flight", "tour"],
        "remove_table_types": ["flight", "tour"],
        "add_blocks": ["insurance"],
    },
    "2026-07-04-china-high-speed-train-survival-guide-booking-classes-and-insider-tips.md": {
        "remove_blocks": ["flight", "tour"],
        "remove_table_types": ["flight", "tour"],
        "add_blocks": ["esim", "insurance"],
    },
    "2026-07-12-navigating-chinas-transportation-a-californians-guide-for-european-travelers.md": {
        "remove_blocks": ["hotel", "flight", "tour"],
        "remove_table_types": ["hotel", "flight", "tour"],
    },
    "2026-07-14-transportation-guide-guide.md": {
        "remove_blocks": ["hotel", "flight", "tour"],
        "remove_table_types": ["hotel", "flight", "tour"],
    },
    "2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md": {
        "remove_blocks": ["hotel", "flight", "tour"],
        "remove_table_types": ["hotel", "flight", "tour"],
        "add_blocks": ["esim"],
    },
    "china-transportation-card-guide.md": {
        "remove_affiliate_link_keys": ["hotel"],
    },
    "china-airport-transfer-guide.md": {
        "remove_affiliate_link_keys": ["hotel"],
    },

    # === HOTEL / ACCOMMODATION ===
    "2026-07-27-accommodation-tips-guide.md": {
        "remove_blocks": ["flight"],
        "remove_table_types": ["flight"],
    },

    # === eSIM / INTERNET / VPN ===
    "internet-connection-china-esim-vpn-guide.md": {
        "remove_blocks": ["hotel", "flight", "insurance", "tour"],
        "remove_table_types": ["hotel", "flight", "insurance", "tour"],
        "remove_inline": ["klook-link"],
        "remove_callouts_containing": ["klook-link"],
    },

    # === TRAVEL INSURANCE ===
    "best-travel-insurance-china.md": {
        "remove_blocks": ["flight", "tour"],
        "remove_table_types": ["flight", "tour"],
    },

    # === FOOD / CUISINE ===
    "2026-05-28-chinese-food-delivery-meituan-eleme-guide.md": {
        "remove_blocks": ["hotel", "flight"],
        "remove_table_types": ["hotel", "flight"],
    },
    "2026-06-22-chinese-tea-culture-history-types-and-tea-ceremony-guide.md": {
        "remove_blocks": ["hotel", "flight"],
        "remove_table_types": ["hotel", "flight"],
    },
    "2026-06-23-sichuan-hotpot-guide-history-best-restaurants-and-cultural-significance.md": {
        "remove_blocks": ["hotel", "flight"],
        "remove_table_types": ["hotel", "flight"],
    },
    "2026-07-06-a-gastronomic-adventure-in-china-a-foodies-guide-for-european-travelers.md": {
        "remove_blocks": ["hotel", "flight"],
        "remove_table_types": ["hotel", "flight"],
    },
    "2026-07-10-a-gastronomic-adventure-in-china-food-recommendations-for-international-travelers.md": {
        "remove_blocks": ["hotel"],
        "remove_table_types": ["hotel"],
        "add_blocks": ["esim"],
    },
    "2026-07-16-food-recommendations-guide.md": {
        "remove_blocks": ["hotel", "flight"],
        "remove_table_types": ["hotel", "flight"],
    },

    # === PHOTOGRAPHY ===
    "2026-08-01-china-photography-guide-capturing-the-wonders-of-the-middle-kingdom.md": {
        "remove_blocks": ["hotel", "tour"],
        "remove_table_types": ["hotel", "tour"],
    },

    # === SAFETY ===
    "2026-05-26-is-china-safe-for-tourists-2026-honest-assessment.md": {
        "remove_blocks": ["hotel", "tour"],
        "remove_table_types": ["hotel", "tour"],
    },
    "2026-07-13-navigating-china-with-confidence-a-californians-guide-to-travel-safety.md": {
        "remove_blocks": ["hotel", "tour"],
        "remove_table_types": ["hotel", "tour"],
        "add_blocks": ["esim"],
    },
    "2026-07-16-is-china-safe-for-tourists-2026-honest-safety-assessment.md": {
        "remove_blocks": ["hotel", "tour"],
        "remove_table_types": ["hotel", "tour"],
    },
    "2026-07-20-travel-safety-guide.md": {
        "remove_blocks": ["hotel", "tour"],
        "remove_table_types": ["hotel", "tour"],
    },

    # === LANGUAGE (not in table - judge by user need) ===
    "2026-08-03-chinese-language-survival-phrases-guide.md": {
        "remove_blocks": ["hotel", "tour"],
        "remove_table_types": ["hotel", "tour"],
    },
}


def remove_block_cta(lines, cta_type):
    """Remove lines that are exactly {{< affiliate-cta_type >}} and following blank line."""
    result = []
    i = 0
    pattern = re.compile(r'^\s*\{\{<\s*affiliate-' + re.escape(cta_type) + r'\s*>\}\}\s*$')
    while i < len(lines):
        if pattern.match(lines[i]):
            # Skip this line
            i += 1
            # Skip following blank line if present
            if i < len(lines) and lines[i].strip() == '':
                i += 1
            continue
        result.append(lines[i])
        i += 1
    return result


def remove_table_rows(lines, cta_types):
    """Remove table rows containing {{< affiliate-X >}} for X in cta_types."""
    result = []
    for line in lines:
        remove = False
        for ct in cta_types:
            if ('{{< affiliate-' + ct + ' >}}') in line or ('{{< affiliate-' + ct) in line:
                # Only remove if it's a table row (starts with |)
                if line.strip().startswith('|'):
                    remove = True
                    break
        if not remove:
            result.append(line)
    return result


def remove_inline_shortcodes(lines, shortcode_names):
    """Remove inline shortcode calls like {{< booking-link "text" />}} from lines."""
    result = []
    for line in lines:
        new_line = line
        for sc in shortcode_names:
            # Match {{< scname ... />}} or {{< scname ... >}}...{{< /scname >}}
            pattern = r'\{\{<\s*' + re.escape(sc) + r'[^>]*?/\s*>\}\}'
            new_line = re.sub(pattern, '', new_line)
            # Also handle non-self-closing with inner content
            pattern2 = r'\{\{<\s*' + re.escape(sc) + r'[^>]*>\}\}.*?\{\{<\s*/' + re.escape(sc) + r'\s*>\}\}'
            new_line = re.sub(pattern2, '', new_line)
        # Clean up double spaces and empty parens
        new_line = re.sub(r'\(\s*\)', '', new_line)
        new_line = re.sub(r'  +', ' ', new_line)
        result.append(new_line)
    return result


def remove_callout_lines(lines, shortcode_names):
    """Remove entire blockquote lines (starting with >) that contain specified shortcodes."""
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('>'):
            remove = False
            for sc in shortcode_names:
                if ('{{<' + sc) in stripped or ('{{< ' + sc) in stripped:
                    remove = True
                    break
            if remove:
                # Also skip following blank line
                continue
        result.append(line)
    return result


def fix_mid_cta(lines, partner_map):
    """Change partner="X" to partner="Y" in affiliate-mid-cta calls."""
    result = []
    for line in lines:
        new_line = line
        if 'affiliate-mid-cta' in line:
            for old, new in partner_map.items():
                new_line = new_line.replace(f'partner="{old}"', f'partner="{new}"')
                # Also update text if it mentions the old partner
                if old == 'hotel' and new == 'esim':
                    new_line = new_line.replace('Compare Hotel Options', 'Compare eSIM Options')
                    new_line = new_line.replace('visa_cta_mid_content', 'visa_cta_mid_content')
        result.append(new_line)
    return result


def remove_affiliate_link_table_rows(lines, keys):
    """Remove table rows with affiliate-link key="X" for X in keys."""
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('|') and 'affiliate-link' in stripped:
            remove = False
            for k in keys:
                if f'key="{k}"' in stripped:
                    remove = True
                    break
            if remove:
                continue
        result.append(line)
    return result


def add_block_ctas(lines, cta_types):
    """Add affiliate block CTAs after the last remaining affiliate block CTA."""
    if not cta_types:
        return lines
    
    # Find the last block CTA line
    last_cta_idx = -1
    block_pattern = re.compile(r'^\s*\{\{<\s*affiliate-(hotel|flight|insurance|esim|tour)\s*>\}\}\s*$')
    for i, line in enumerate(lines):
        if block_pattern.match(line):
            last_cta_idx = i
    
    if last_cta_idx == -1:
        # No block CTAs found - append at end before final ---
        # Find last horizontal rule
        insert_idx = len(lines)
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip() == '---':
                insert_idx = i
                break
        new_ctas = []
        for ct in cta_types:
            new_ctas.append('')
            new_ctas.append(f'{{{{< affiliate-{ct} >}}}}')
        new_ctas.append('')
        return lines[:insert_idx] + new_ctas + lines[insert_idx:]
    
    # Insert after last CTA (and its following blank line)
    insert_idx = last_cta_idx + 1
    # Skip blank line after last CTA
    while insert_idx < len(lines) and lines[insert_idx].strip() == '':
        insert_idx += 1
    
    new_ctas = []
    for ct in cta_types:
        new_ctas.append('')
        new_ctas.append(f'{{{{< affiliate-{ct} >}}}}')
    
    return lines[:insert_idx] + new_ctas + [''] + lines[insert_idx:]


def deduplicate_block_ctas(lines):
    """Remove duplicate consecutive affiliate block CTAs of the same type."""
    result = []
    seen_types = set()
    block_pattern = re.compile(r'^\s*\{\{<\s*affiliate-(hotel|flight|insurance|esim|tour)\s*>\}\}\s*$')
    for line in lines:
        m = block_pattern.match(line)
        if m:
            ct = m.group(1)
            if ct in seen_types:
                # Skip this duplicate and following blank line
                continue
            seen_types.add(ct)
        result.append(line)
    return result


def process_file(filename, config):
    filepath = os.path.join(POSTS_DIR, filename)
    if not os.path.exists(filepath):
        print(f"  WARNING: {filename} not found!")
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    original_len = len(lines)
    
    # 1. Remove callout lines containing specific shortcodes
    if 'remove_callouts_containing' in config:
        lines = remove_callout_lines(lines, config['remove_callouts_containing'])
    
    # 2. Remove inline shortcodes
    if 'remove_inline' in config:
        lines = remove_inline_shortcodes(lines, config['remove_inline'])
    
    # 3. Remove block CTAs
    if 'remove_blocks' in config:
        for ct in config['remove_blocks']:
            lines = remove_block_cta(lines, ct)
    
    # 4. Remove table rows
    if 'remove_table_types' in config:
        lines = remove_table_rows(lines, config['remove_table_types'])
    
    # 5. Remove affiliate-link table rows
    if 'remove_affiliate_link_keys' in config:
        lines = remove_affiliate_link_table_rows(lines, config['remove_affiliate_link_keys'])
    
    # 6. Fix mid-cta partner
    if 'mid_cta_fix' in config:
        lines = fix_mid_cta(lines, config['mid_cta_fix'])
    
    # 7. Deduplicate block CTAs
    lines = deduplicate_block_ctas(lines)
    
    # 8. Add missing CTAs
    if 'add_blocks' in config:
        lines = add_block_ctas(lines, config['add_blocks'])
    
    # Clean up: remove triple+ blank lines, remove trailing spaces
    new_content = '\n'.join(lines)
    new_content = re.sub(r'\n{4,}', '\n\n\n', new_content)
    new_content = re.sub(r'[ \t]+\n', '\n', new_content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"  {filename}: {original_len} -> {len(new_content.split(chr(10)))} lines")
    return True


def main():
    print("=" * 60)
    print("P0-5: Affiliate Intent Mismatch Fix")
    print("=" * 60)
    
    total = len(FIXES)
    success = 0
    for filename, config in FIXES.items():
        print(f"\nProcessing: {filename}")
        if process_file(filename, config):
            success += 1
    
    print(f"\n{'=' * 60}")
    print(f"Done: {success}/{total} files processed")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
