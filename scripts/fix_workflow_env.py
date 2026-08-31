#!/usr/bin/env python3
"""Insert env block into cross-agent-learning workflow files."""
import sys

def insert_env_block(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    env_block = """
    env:
      # GA4
      GA4_API_KEY: ${{ secrets.GA4_API_KEY }}
      GA4_PROPERTY_ID: ${{ secrets.GA4_PROPERTY_ID }}
      GA4_SERVICE_ACCOUNT_JSON: ${{ secrets.GA4_SERVICE_ACCOUNT_JSON }}
      # GSC
      GSC_SERVICE_ACCOUNT_JSON: ${{ secrets.GSC_SERVICE_ACCOUNT_JSON }}
      GSC_SITE_URL: ${{ secrets.GSC_SITE_URL }}
      # Travelpayouts
      TRAVELPAYOUTS_API_TOKEN: ${{ secrets.TRAVELPAYOUTS_API_TOKEN }}
      TRAVELPAYOUTS_MARKER: ${{ secrets.TRAVELPAYOUTS_MARKER }}
      TRAVELPAYOUTS_DRIVE_ID: ${{ secrets.TRAVELPAYOUTS_DRIVE_ID }}
      # MailerLite
      MAILERLITE_API_TOKEN: ${{ secrets.MAILERLITE_API_TOKEN }}
      # Buffer
      BUFFER_WORKER_URL: ${{ secrets.BUFFER_WORKER_URL }}
      NEW_BUFFER_WORKER_URL: ${{ secrets.NEW_BUFFER_WORKER_URL }}
      BUFFER_API_TOKEN_A: ${{ secrets.BUFFER_API_TOKEN_A }}
      BUFFER_API_TOKEN_B: ${{ secrets.BUFFER_API_TOKEN_B }}
      # Cloudflare
      CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
      CLOUDFLARE_ZONE_ID: ${{ secrets.CLOUDFLARE_ZONE_ID }}
      # Feishu
      FEISHU_WEBHOOK_URL: ${{ secrets.FEISHU_WEBHOOK_URL }}
      FEISHU_SECRET: ${{ secrets.FEISHU_SECRET }}
"""

    # Try different patterns for insertion point
    patterns = [
        ('    timeout-minutes: 45\n\n    steps:', '    timeout-minutes: 45\n' + env_block + '\n    steps:'),
        ('    timeout-minutes: 60\n\n    steps:', '    timeout-minutes: 60\n' + env_block + '\n    steps:'),
        ('    timeout-minutes: 30\n\n    steps:', '    timeout-minutes: 30\n' + env_block + '\n    steps:'),
    ]

    for old_text, new_text in patterns:
        if old_text in content:
            content = content.replace(old_text, new_text, 1)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f'SUCCESS: env block inserted into {filepath}')
            return True

    print(f'ERROR: Could not find insertion point in {filepath}')
    # Debug: show relevant lines
    lines = content.split('\n')
    for i, line in enumerate(lines[15:30], start=16):
        print(f'  {i}: {repr(line)}')
    return False

if __name__ == '__main__':
    files = [
        '.github/workflows/cross-agent-learning-weekly.yml',
        '.github/workflows/cross-agent-learning-daily.yml',
    ]
    results = []
    for f in files:
        results.append(insert_env_block(f))
    sys.exit(0 if all(results) else 1)
