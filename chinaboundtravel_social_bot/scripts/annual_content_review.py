import os
import glob
from datetime import datetime, timezone

now = datetime.now(timezone.utc)
year = now.year - 1
date_str = now.strftime("%Y-%m-%d")

posts_dir = "content/posts"
all_posts = glob.glob(os.path.join(posts_dir, "*.md"))
total_posts = len(all_posts)

year_review_title = f"{year} in Review: The Complete ChinaBound Travel Year in Numbers"

markdown = f"""---
title: "{year_review_title}"
date: {now.strftime("%Y-%m-%dT%H:%M:%S+00:00")}
lastmod: {now.strftime("%Y-%m-%dT%H:%M:%S+00:00")}
description: "Year {year} was a landmark year for travel between China and the US."
summary: "The {year} annual review from ChinaBound Travel: {total_posts}+ articles published."
tags: ["Annual Review", "China Travel", "Year in Review", "Travel Statistics"]
categories: ["China Essentials"]
ShowToc: true
TocOpen: true
weight: 2
draft: false
---

## {year} at ChinaBound Travel

In {year}, we published {total_posts}+ original articles covering every major aspect of China travel.

### What You Read the Most

1. Visa & Entry Rules
2. Safety & Security
3. Payment Systems
4. Best Time to Visit
5. Packing Lists

### Looking Ahead to {year + 1}

Our focus for next year includes deeper city guides and real-time travel radar.

Thank you for reading in {year}.
We'll see you on the road in {year + 1}.
"""

filepath = os.path.join(posts_dir, f"{date_str}-chinabound-travel-{year}-year-in-review.md")
if not os.path.exists(filepath):
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(markdown)
    print(f"Created annual review: {filepath}")
else:
    print(f"Review already exists: {filepath}")

print("Annual content review completed successfully")
