import re

file_path = r'E:\AI\dulizhan\travel-blog\layouts\cities\single.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
print(f'Total lines: {len(lines)}')
print()
print('--- Lines 89-101 (share buttons area) ---')
for i in range(max(0, 88), min(len(lines), 101)):
    print(f'{i+1:3}: {repr(lines[i][:120])}')

new_block = '''            <a href="https://t.me/share/url?url={{ .Permalink | urlquery }}&text={{ .Title | urlquery }}" target="_blank" rel="noopener noreferrer" class="share-btn share-telegram" title="Share on Telegram">
                <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor" aria-hidden="true"><path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/></svg>
                <span>Telegram</span>
            </a>
            <a href="https://api.whatsapp.com/send?text={{ .Title | urlquery }}%20{{ .Permalink | urlquery }}" target="_blank" rel="noopener noreferrer" class="share-btn share-whatsapp" title="Share on WhatsApp">
                <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor" aria-hidden="true"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 0 1-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 0 1-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 0 1 2.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0 0 12.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 0 0 5.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 0 0-3.48-8.413z"/></svg>
                <span>WhatsApp</span>
            </a>
            <a href="https://reddit.com/submit?url={{ .Permalink | urlquery }}&title={{ .Title | urlquery }}" target="_blank" rel="noopener noreferrer" class="share-btn share-reddit" title="Share on Reddit">
                <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor" aria-hidden="true"><path d="M12 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0zm5.01 4.744c.688 0 1.25.561 1.25 1.249a1.25 1.25 0 0 1-2.498.056l-2.597-.547-.8 3.747c1.824.07 3.48.632 4.674 1.488.308-.309.73-.491 1.207-.491.968 0 1.754.786 1.754 1.754 0 .716-.435 1.333-1.01 1.614a3.111 3.111 0 0 1 .042.52c0 2.694-3.13 4.87-7.004 4.87-3.874 0-7.004-2.176-7.004-4.87 0-.183.015-.366.043-.534A1.748 1.748 0 0 1 4.028 12c0-.968.786-1.754 1.754-1.754.463 0 .898.196 1.207.49 1.207-.883 2.878-1.43 4.744-1.487l.885-4.182a.342.342 0 0 1 .14-.197.35.35 0 0 1 .238-.042l2.906.617a1.214 1.214 0 0 1 1.108-.701zM9.25 12C8.561 12 8 12.562 8 13.25c0 .687.561 1.248 1.25 1.248.687 0 1.248-.561 1.248-1.249 0-.688-.561-1.249-1.249-1.249zm5.5 0c-.687 0-1.248.561-1.248 1.25 0 .687.561 1.248 1.249 1.248.688 0 1.249-.561 1.249-1.249 0-.687-.562-1.249-1.25-1.249zm-5.466 3.99a.327.327 0 0 0-.231.094.33.33 0 0 0 0 .463c.842.842 2.484.913 2.961.913.477 0 2.105-.056 2.961-.913a.361.361 0 0 0 .029-.463.33.33 0 0 0-.464 0c-.547.533-1.684.73-2.512.73-.828 0-1.979-.196-2.512-.73a.326.326 0 0 0-.232-.095z"/></svg>
                <span>Reddit</span>
            </a>
            <a href="https://www.linkedin.com/sharing/share-offsite/?url={{ .Permalink | urlquery }}" target="_blank" rel="noopener noreferrer" class="share-btn share-linkedin" title="Share on LinkedIn">
                <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor" aria-hidden="true"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
                <span>LinkedIn</span>
            </a>
            <a href="mailto:?subject={{ .Title | urlquery }}&body=Check out this guide: {{ .Permalink | urlquery }}" target="_blank" rel="noopener noreferrer" class="share-btn share-email" title="Share via Email">
                <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor" aria-hidden="true"><path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/></svg>
                <span>Email</span>
            </a>
            <button class="share-btn share-copy" onclick="navigator.clipboard.writeText('{{ .Permalink }}');alert('Link copied!')" title="Copy link">
                <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor" aria-hidden="true"><path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>
                <span>Copy</span>
            </button>'''

# Find the line indices: we need to replace from the Telegram button line (the one with share-btn share-telegram on line 91)
# to the end of share-copy button (line 99)
start_idx = None
end_idx = None

for i, line in enumerate(lines):
    if 'share-btn share-telegram' in line and 'https://t.me/' in line:
        # Check if this is still the OLD telegram button (has old SVG, no <span>Telegram</span> nearby)
        # Actually look at the next few lines: if next line has width="20" (not width="28"), it's old
        if start_idx is None:
            # peek ahead at SVG width
            for j in range(i+1, min(i+5, len(lines))):
                if 'width="' in lines[j] and 'height="' in lines[j]:
                    if 'width="20"' in lines[j]:
                        start_idx = i
                        print(f'Start (old telegram btn) at line {i+1}: {repr(lines[i][:100])}')
                    break

    if start_idx is not None and '</button>' in line and 'share-copy' in line:
        end_idx = i
        print(f'End (share-copy button) at line {i+1}: {repr(lines[i][:100])}')
        break

if start_idx is None or end_idx is None:
    # Try broader: find old share-icon share-email and share-icon share-copy
    print('First approach failed, trying fallback: find share-icon markers')
    for i, line in enumerate(lines):
        if start_idx is None and 'share-telegram' in line:
            start_idx = i
            print(f'Start at line {i+1}: {repr(lines[i][:100])}')
        if start_idx is not None and '<button' in line and 'share-icon share-copy' in line:
            # this is the OLD share-copy button line; end is its </button>
            # find the </button> on this or next line
            end_idx = i
            if '</button>' not in lines[i]:
                for j in range(i+1, min(i+5, len(lines))):
                    if '</button>' in lines[j]:
                        end_idx = j
                        break
            print(f'End at line {end_idx+1}')
            break

if start_idx is None or end_idx is None:
    print('FAILED to find region! Dumping all share-icon / share-btn occurrences:')
    for i, line in enumerate(lines):
        if 'share-icon' in line or 'share-btn' in line:
            print(f'  {i+1}: {repr(line[:140])}')
    exit(1)

print(f'\nReplacing lines {start_idx+1} to {end_idx+1} (inclusive)...')
new_lines = lines[:start_idx] + [new_block] + lines[end_idx+1:]
new_content = '\n'.join(new_lines)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)
print('DONE - file updated.')

# Also: remove any remaining old-style share-icon elements with width="20" (sanity check)
with open(file_path, 'r', encoding='utf-8') as f:
    verify = f.read()
if 'share-icon' in verify:
    print('WARNING: still found "share-icon" in file!')
    for i, line in enumerate(verify.split('\n')):
        if 'share-icon' in line:
            print(f'  {i+1}: {repr(line[:140])}')
else:
    print('VERIFIED: all share-icon occurrences replaced.')
if '$pageurl' in verify or '$title' in verify:
    print('WARNING: still found $pageurl/$title!')
    for i, line in enumerate(verify.split('\n')):
        if '$pageurl' in line or '$title' in line:
            print(f'  {i+1}: {repr(line[:140])}')
else:
    print('VERIFIED: no remaining $pageurl/$title references.')
