# chinaboundtravel Social Media Bot

Automated social media posting system for [chinaboundtravel.com](https://chinaboundtravel.com) - an English-language China travel blog by Joran.

## Overview

This bot handles automated content distribution across multiple social media platforms:
- Reddit
- Pinterest
- Quora
- Medium

## Features

- RSS feed integration for automatic content fetching
- Platform-specific posting (Phase 1: Framework ready)
- Rate limiting and daily posting limits
- Compliance with Reddit's no-external-links policy
- Multi-language support (English content)
- Comprehensive logging

## Author

**Joran** - California native, Chengdu son-in-law, 10+ years of China travel experience.

## Directory Structure

```
chinaboundtravel_social_bot/
├── main.py                  # Main scheduler
├── config.py                # Global configuration
├── test_connections.py     # API connectivity test
├── requirements.txt         # Python dependencies
├── modules/                 # Platform modules
│   ├── reddit_poster.py
│   ├── pinterest_poster.py
│   ├── quora_poster.py
│   └── medium_poster.py
├── content/                 # Content resources
│   ├── initial_posts.csv    # 10 blog posts
│   └── templates/           # Platform templates
│       ├── reddit_templates.md
│       ├── pinterest_templates.md
│       ├── quora_templates.md
│       └── medium_templates.md
└── README.md
```

## Requirements

- Python 3.9+
- pip package manager
- Accounts on target platforms (Reddit, Pinterest, Quora, Medium)

## Installation

### 1. Clone or Extract

```bash
# If you have git:
git clone <repository-url>
cd chinaboundtravel_social_bot

# Or extract the ZIP file
unzip chinaboundtravel_social_bot.zip
cd chinaboundtravel_social_bot
```

### 2. Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## Configuration

### 1. Copy config.py

All credentials must be configured in `config.py`. Each platform section includes detailed instructions.

### 2. Platform Credentials

#### Reddit
1. Go to [Reddit Apps](https://www.reddit.com/prefs/apps)
2. Create a new app (script type)
3. Copy Client ID and Client Secret
4. Fill in your Reddit username and password

```python
REDDIT_CONFIG = {
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "username": "YOUR_USERNAME",
    "password": "YOUR_PASSWORD",
    # ...
}
```

#### Pinterest
1. Go to [Pinterest Developers](https://developers.pinterest.com/apps/)
2. Create a new app
3. Get App ID, App Secret, and Access Token

```python
PINTEREST_CONFIG = {
    "app_id": "YOUR_APP_ID",
    "app_secret": "YOUR_APP_SECRET",
    "access_token": "YOUR_ACCESS_TOKEN",
    # ...
}
```

#### Quora
1. Log in to Quora
2. Get cookies (m_bc, m_s, m_ts)
3. Or use email/password

```python
QUORA_CONFIG = {
    "email": "YOUR_EMAIL",
    "password": "YOUR_PASSWORD",
    # Or use cookies
    "m_bc": "YOUR_M_BC_COOKIE",
    # ...
}
```

#### Medium
1. Go to [Medium Settings](https://medium.com/me/settings/security)
2. Generate an Integration Token

```python
MEDIUM_CONFIG = {
    "integration_token": "YOUR_TOKEN",
    "user_id": "YOUR_USER_ID",
    # ...
}
```

## Testing

Run the connectivity test to verify all configurations:

```bash
python test_connections.py
```

Expected output:
```
============================================================
  chinaboundtravel.com Social Bot - Connection Test
============================================================

Testing: https://chinaboundtravel.com
Author: Joran

Dependencies Check
  [OK] requests installed
  [OK] praw installed
  ...

Test Summary
  [OK] Dependencies: All required packages installed
  [OK] Blog RSS: Connected
  [OK] Reddit: Connected
  [WARN] Pinterest: Skipped (not configured)
  [WARN] Quora: Skipped (not configured)
  [OK] Medium: Connected

Results: 3/6 passed, 3 skipped
```

## Usage

### Run Once (Manual Trigger)

```bash
python main.py --once
```

### Run Scheduler (Continuous)

```bash
python main.py --continuous
```

The bot will post according to the schedule in `config.py`:
- Morning batch: 10:00 AM Beijing time
- Afternoon batch: 4:00 PM Beijing time

### Daily Posting Limits

| Platform | Daily Limit |
|----------|-------------|
| Reddit | 3 posts |
| Pinterest | 10 pins |
| Quora | 5 answers |
| Medium | 2 articles |

## Compliance Rules

### Reddit (STRICT)
Reddit does NOT allow external links in posts. All Reddit posts must use:

```
I wrote a fully detailed guide on my blog. Comment 'GUIDE' below, and I'll DM you the link.
```

The bot automatically enforces this rule.

## Common Issues

### Issue: "PRAW not installed"
```
Solution: pip install praw
```

### Issue: "Access token not configured"
```
Solution: Complete Pinterest API setup in config.py
```

### Issue: "Quora requires browser automation"
```
Solution: Quora's full API requires Selenium/browser automation.
This is planned for Phase 2.
```

### Issue: UnicodeEncodeError
```
Solution: Set environment variable
Windows: set PYTHONIOENCODING=utf-8
Mac/Linux: export PYTHONIOENCODING=utf-8
```

## Phase Status

| Phase | Status | Features |
|-------|--------|----------|
| Phase 1 | ✅ Complete | Framework, config, connectivity test, RSS fetching |
| Phase 2 | Planned | Full automated posting, Selenium for Quora |
| Phase 3 | Planned | Analytics, reporting, AI content generation |

## Logging

Logs are written to:
- Console (stdout)
- `social_bot.log` file

Log rotation is enabled (10MB max, 5 backups).

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify all credentials are correct in `config.py`
3. Run `python test_connections.py` for detailed diagnostics

## License

Private project for chinaboundtravel.com

---

*Built for Joran by the ChinaBound Travel Team*

Last updated: 2026-05-26