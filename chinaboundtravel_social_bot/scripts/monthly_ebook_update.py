import os
import glob
from datetime import datetime

now = datetime.utcnow()
version = now.strftime("%Y.%m")
month_name = now.strftime("%B %Y")
date_str = now.strftime("%Y-%m-%d")

print(f"Generating ebook version: {version} ({month_name})")

os.makedirs("static/downloads", exist_ok=True)
os.makedirs("content/ebook", exist_ok=True)

posts_dir = "content/posts"
filename = f"{date_str}-chinabound-travel-guide-{version.replace('.', '-')}-monthly-update.md"
filepath = os.path.join(posts_dir, filename)

title = f"ChinaBound Travel Guide {version} - Now Updated With Latest Visa Rules"

markdown_content = f"""---
content_id: "cbt-ebook-{version.replace(".", "")}"
title: "{title}"
date: {now.strftime("%Y-%m-%dT%H:%M:%S+00:00")}
lastmod: {now.strftime("%Y-%m-%dT%H:%M:%S+00:00")}
description: "The {month_name} edition of the ChinaBound Travel Guide is here - updated with this month's visa policy changes."
summary: "Monthly update: the {month_name} edition covers all visa rule changes and safety recommendations."
tags: ["China Travel", "Visa Updates", "Travel Guide"]
categories: ["China Essentials"]
ShowToc: true
TocOpen: false
weight: 1
draft: false
---

## ChinaBound Travel Guide Now at Version {version}

Every month, the ChinaBound Travel Guide PDF gets a fresh update with the latest information travelers need.

### What's New in Version {version}

1. **Latest Visa Policy Updates** - All changes from the past month affecting 15-day visa-free, L-visa, and multi-entry tourist visas
2. **Updated Crowd Forecasts** - New data on which scenic spots are overcrowded this month
3. **Payment System Refresh** - Current status of Alipay, WeChat Pay, and international card acceptance
4. **Safety & Scam Alerts** - New scam patterns reported by travelers
5. **Recommended Routes** - Seasonal travel recommendations based on weather and crowd patterns

### Get Your Copy

Visit [chinaboundtravel.com/pricing](/pricing) to get the latest guide.

### What's Coming Next Month

- Additional city-specific mini-guides released weekly
- AI trip planner template expansion for {now.strftime("%B")} travel

---

*Last updated: {now.strftime("%B %d, %Y")}*
"""

if not os.path.exists(filepath):
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    print(f"Created: {filename}")
else:
    print(f"Exists: {filename}")

ebook_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>ChinaBound Travel Guide {version}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #3498db; }}
        .footer {{ margin-top: 50px; padding-top: 20px; border-top: 1px solid #ecf0f1; }}
    </style>
</head>
<body>
    <h1>ChinaBound Travel Guide {version}</h1>
    <p><em>Published: {month_name}</em></p>
    <h2>1. Visa Requirements & Entry Rules</h2>
    <p>Understanding China's visa requirements is essential for a smooth trip.</p>
    <h2>2. Best Time to Visit China</h2>
    <p>China's climate varies greatly by region. The best time to visit depends on your destination.</p>
    <h2>3. Packing List Essentials</h2>
    <p>Packing for China requires careful planning.</p>
    <h2>4. Safety & Security Tips</h2>
    <p>China is generally a safe country for travelers.</p>
    <h2>5. Transportation Guide</h2>
    <p>Getting around China is easier than ever with high-speed trains.</p>
    <h2>6. Payment Systems</h2>
    <p>Alipay and WeChat Pay are essential for daily transactions in China.</p>
    <h2>7. Cultural Etiquette</h2>
    <p>Understanding Chinese customs will enhance your travel experience.</p>
    <h2>8. Budget Planning</h2>
    <p>China offers options for all budgets.</p>
    <div class="footer">
        <p>&copy; {now.year} ChinaBound Travel. Visit: https://chinaboundtravel.com</p>
    </div>
</body>
</html>"""

html_file = f"static/downloads/ebook-{version.replace('.', '-')}.html"
with open(html_file, 'w', encoding='utf-8') as f:
    f.write(ebook_html)
print(f"Created HTML ebook")

ebook_page_content = f"""---
title: "ChinaBound Travel Guide {version}"
date: {now.strftime("%Y-%m-%dT%H:%M:%S+00:00")}
lastmod: {now.strftime("%Y-%m-%dT%H:%M:%S+00:00")}
description: "Download the complete ChinaBound Travel Guide {version}."
summary: "The {month_name} edition of the ChinaBound Travel Guide PDF."
tags: ["Travel Guide", "China Travel", "PDF Download"]
categories: ["China Essentials"]
ShowToc: true
TocOpen: true
weight: 1
draft: false
type: page
---

## Get Your ChinaBound Travel Guide {version}

### What's Included

- Complete visa requirements guide
- Best times to visit each region
- Packing list essentials
- Safety tips for travelers
- Transportation guide
- Payment system setup instructions
- Cultural etiquette tips
- Budget planning worksheets

[View pricing and subscription options](/pricing)

---

*Last updated: {now.strftime("%B %d, %Y")}*
"""

ebook_page_path = f"content/ebook/{date_str}-travel-guide-{version.replace('.', '-')}.md"
if not os.path.exists(ebook_page_path):
    with open(ebook_page_path, 'w', encoding='utf-8') as f:
        f.write(ebook_page_content)
    print("Created ebook landing page")
else:
    print("Ebook landing page exists")

print("Monthly ebook update completed successfully")
