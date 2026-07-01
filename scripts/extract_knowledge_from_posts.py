"""
Extract knowledge from existing Hugo blog posts into the content knowledge base.
This populates config/content_knowledge_base.json with real information from published articles,
enabling Joran's AI content generation to reference actual site content.

Usage:
  python scripts/extract_knowledge_from_posts.py
  python scripts/extract_knowledge_from_posts.py --post-dir content/posts --config-dir config
"""

import os
import re
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


class PostKnowledgeExtractor:
    def __init__(self, repo_path: str, post_dir: str = "content/posts", config_dir: str = "config"):
        self.repo_path = Path(repo_path)
        self.post_dir = self.repo_path / post_dir
        self.kb_path = self.repo_path / config_dir / "content_knowledge_base.json"
        self.kb = self._load_kb()

        # Skip directories
        self.skip_dirs = {".archived", ".audit_backup", "drafts"}

        # Category classification keywords
        self.category_keywords = {
            "destinations": ["attraction", "mountain", "park", "lake", "temple", "wall", "city guide",
                             "must see", "scenic", "landmark", "ancient city", "viewpoint", "cave", "bridge"],
            "transportation": ["high speed rail", "hsr", "metro", "subway", "train station", "flight",
                               "airport", "bus", "taxi", "transport", "drive", "ride", "ticket booking",
                               "rail", "booking"],
            "accommodation": ["hotel", "hostel", "stay", "lodging", "accommodation", "airbnb", "inn",
                             "sleep"],
            "food": ["food", "cuisine", "hotpot", "restaurant", "street food", "dumpling", "noodle",
                    "tea", "tea culture", "delivery", "meituan", "eleme", "dining", "drink",
                    "peppercorn", "spicy", "culinary"],
            "culture": ["culture", "history", "traditional", "festival", "custom", "ceremony",
                       "heritage", "dynasty", "ancient", "religion", "temple", "art", "confucian",
                       "taoism", "buddhism", "tradition"],
            "tips": ["guide", "tip", "advice", "warning", "avoid", "best practice", "hack",
                    "survive", "mistake", "lesson", "recommendation", "practical"],
            "seasons": ["season", "best time", "weather", "climate", "spring", "summer", "winter",
                       "autumn", "rainy", "temperature"],
            "budget": ["budget", "cost", "price", "save", "affordable", "cheap", "expensive",
                      "free", "ticket price", "fee", "money", "currency", "rmb", "yuan",
                      "how much"],
            "safety": ["safety", "safe", "danger", "caution", "scam", "secure", "emergency",
                      "police", "insurance"],
            "visa": ["visa", "entry", "customs", "immigration", "passport", "transit",
                    "144-hour", "visa-free", "visa free", "permit", "border"]
        }

    def _load_kb(self):
        if self.kb_path.exists():
            with open(self.kb_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self._empty_kb()

    def _empty_kb(self):
        return {
            "version": "1.1",
            "last_updated": datetime.now().isoformat(),
            "total_entries": 0,
            "sources": ["xiaohongshu", "douyin", "zhihu", "mafengwo", "ctrip", "weibo", "blog"],
            "knowledge_categories": {
                "destinations": [],
                "transportation": [],
                "accommodation": [],
                "food": [],
                "culture": [],
                "tips": [],
                "seasons": [],
                "budget": [],
                "safety": [],
                "visa": []
            },
            "learning_metrics": {
                "total_learned": 0,
                "total_deduplicated": 0,
                "total_filtered": 0,
                "last_learning_date": ""
            }
        }

    def _save_kb(self):
        self.kb["version"] = "1.1"
        self.kb["last_updated"] = datetime.now().isoformat()
        self.kb["learning_metrics"]["last_learning_date"] = datetime.now().strftime("%Y-%m-%d")
        with open(self.kb_path, 'w', encoding='utf-8') as f:
            json.dump(self.kb, f, indent=2, ensure_ascii=False)

    def _generate_hash(self, content: str) -> str:
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def _is_duplicate(self, content_hash: str) -> bool:
        for category, entries in self.kb["knowledge_categories"].items():
            for entry in entries:
                if entry.get("hash") == content_hash:
                    return True
        return False

    def _classify(self, title: str, content: str) -> str:
        """Classify content into a knowledge category using keyword matching."""
        text_lower = (title + " " + content).lower()
        scores = {}

        for category, keywords in self.category_keywords.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            scores[category] = score

        if not any(scores.values()):
            return "tips"

        return max(scores, key=scores.get)

    def _extract_key_points(self, title: str, content: str, slug: str) -> List[str]:
        """Extract key practical points from article content."""
        key_points = []

        # Extract H2 headings as key topics
        h2_matches = re.findall(r'^##\s+(.+)$', content, re.MULTILINE)
        for h2 in h2_matches[:8]:
            h2_clean = re.sub(r'\*+', '', h2).strip()
            if 10 < len(h2_clean) < 100:
                key_points.append(f"Section: {h2_clean}")

        # Extract numbered/bulleted tips
        tip_patterns = [
            r'^\d+\.\s+(.{20,120})$',
            r'^[-*]\s+(.{20,120})$',
            r'^\s+\d+\.\s+(.{20,120})$',
        ]
        for pattern in tip_patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            for m in matches[:5]:
                m_clean = re.sub(r'\*+', '', m).strip()
                if len(m_clean) > 15:
                    key_points.append(m_clean)

        # Extract practical info (prices, times, addresses)
        practical_patterns = [
            r'(\$?\d+\s*(?:RMB|USD|yuan|CNY)?[\w\s]{5,50})',
            r'(?:open|opens?|hours?)\s*(?:from|:)\s*(.{10,60})',
            r'(?:cost|price|fee|ticket)\s*(?:is|:)\s*(.{10,60})',
            r'(?:best time|recommended)\s*(?:to|:)\s*(.{10,60})',
        ]
        for pattern in practical_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for m in matches[:3]:
                m_clean = m.strip()
                if 10 < len(m_clean) < 80:
                    key_points.append(f"Practical: {m_clean}")

        # Extract mentions of specific places/locations
        if "zhangjiajie" in slug:
            places = ["Yuanjiajie", "Tianzi Mountain", "Golden Whip Stream", "Tianmen Mountain",
                      "Tianmen Cave", "Glass Skywalk", "Huangshi Village", "Avatar Hallelujah Mountain"]
            for place in places:
                if place.lower() in content.lower() and place not in str(key_points):
                    key_points.append(f"Place: {place}")

        # Deduplicate and limit
        seen = set()
        unique_points = []
        for p in key_points:
            p_lower = p.lower()
            if p_lower not in seen:
                seen.add(p_lower)
                unique_points.append(p)
            if len(unique_points) >= 12:
                break

        return unique_points[:10]

    def _extract_summary(self, title: str, content: str, max_len: int = 500) -> str:
        """Extract a concise summary from the article."""
        # Try to find the first substantial paragraph after the intro
        paragraphs = re.split(r'\n\s*\n', content)

        summary_parts = []
        for p in paragraphs:
            p = p.strip()
            # Skip headers, image lines, empty lines
            if not p or p.startswith('#') or p.startswith('[') or p.startswith('|') or p.startswith('!'):
                continue
            # Skip short lines
            if len(p) < 30:
                continue
            # Clean markdown
            p = re.sub(r'\*+', '', p)
            p = re.sub(r'\[.*?\]\(.*?\)', '', p)
            p = p.strip()
            if p:
                summary_parts.append(p)

        summary = ' '.join(summary_parts[:5])
        if len(summary) > max_len:
            summary = summary[:max_len] + "..."
        return summary

    def _get_post_files(self) -> List[Path]:
        """Get all markdown post files, excluding archived/backup/draft directories."""
        post_files = []
        if not self.post_dir.exists():
            return post_files

        for md_file in self.post_dir.rglob("*.md"):
            # Skip files in excluded directories
            rel_parts = md_file.relative_to(self.post_dir).parts
            if any(part in self.skip_dirs for part in rel_parts):
                continue
            post_files.append(md_file)

        return sorted(post_files, key=lambda f: f.stat().st_mtime, reverse=True)

    def _parse_frontmatter(self, content: str) -> Dict[str, Any]:
        """Extract frontmatter from Hugo markdown file."""
        if not content.startswith('---'):
            return {}

        parts = content.split('---', 2)
        if len(parts) < 3:
            return {}

        fm_text = parts[1]
        fm = {}

        # Parse simple key-value pairs
        for line in fm_text.strip().split('\n'):
            line = line.strip()
            if ':' in line and not line.startswith('-'):
                key, _, value = line.partition(':')
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                fm[key] = value

        return fm

    def extract_from_all_posts(self) -> Dict[str, Any]:
        """Main extraction method: scan all posts and populate knowledge base."""
        post_files = self._get_post_files()
        print(f"[Extract] Found {len(post_files)} post files")

        stats = {
            "total_scanned": 0,
            "total_extracted": 0,
            "total_duplicates": 0,
            "total_filtered": 0,
            "posts_processed": [],
            "category_counts": {}
        }

        for post_file in post_files:
            try:
                with open(post_file, 'r', encoding='utf-8') as f:
                    raw = f.read()

                if len(raw) < 200:
                    stats["total_filtered"] += 1
                    continue

                # Parse frontmatter
                fm = self._parse_frontmatter(raw)
                title = fm.get("title", post_file.stem)
                slug = fm.get("slug", post_file.stem)
                tags = fm.get("tags", [])

                # Extract body content (after frontmatter)
                body = raw
                if raw.startswith('---'):
                    parts = raw.split('---', 2)
                    if len(parts) >= 3:
                        body = parts[2]

                stats["total_scanned"] += 1

                # Classify category
                category = self._classify(title, body)

                # Extract key points
                key_points = self._extract_key_points(title, body, slug)
                if len(key_points) < 2:
                    stats["total_filtered"] += 1
                    continue

                # Extract summary
                summary = self._extract_summary(title, body)

                # Generate hash for dedup
                content_hash = self._generate_hash(title + summary[:200])

                if self._is_duplicate(content_hash):
                    stats["total_duplicates"] += 1
                    continue

                # Create knowledge entry
                entry = {
                    "hash": content_hash,
                    "source": "blog_post",
                    "url": f"https://chinaboundtravel.com/posts/{slug}/",
                    "keyword": title,
                    "slug": slug,
                    "tags": tags if isinstance(tags, list) else [tags],
                    "category": category,
                    "content": summary,
                    "key_points": key_points,
                    "language": "en",
                    "learned_at": datetime.now().isoformat(),
                    "relevance": len(key_points)
                }

                # Add to knowledge base
                self.kb["knowledge_categories"][category].append(entry)
                self.kb["total_entries"] += 1
                stats["total_extracted"] += 1
                stats["category_counts"][category] = stats["category_counts"].get(category, 0) + 1

                print(f"  [+] {title[:50]}... -> {category} ({len(key_points)} key_points)")

                stats["posts_processed"].append({
                    "title": title[:80],
                    "slug": slug,
                    "category": category,
                    "key_points_count": len(key_points)
                })

            except Exception as e:
                print(f"  [!] Error processing {post_file.name}: {e}")

        # Save the updated knowledge base
        self.kb["learning_metrics"]["total_learned"] += stats["total_extracted"]
        self.kb["learning_metrics"]["total_deduplicated"] += stats["total_duplicates"]
        self.kb["learning_metrics"]["total_filtered"] += stats["total_filtered"]
        self._save_kb()

        return stats

    def print_summary(self, stats: Dict[str, Any]):
        print("\n" + "=" * 60)
        print("KNOWLEDGE EXTRACTION SUMMARY")
        print("=" * 60)
        print(f"Posts scanned:        {stats['total_scanned']}")
        print(f"Knowledge extracted:  {stats['total_extracted']}")
        print(f"Duplicates skipped:   {stats['total_duplicates']}")
        print(f"Filtered (low quality): {stats['total_filtered']}")
        print(f"\nTotal KB entries:     {self.kb['total_entries']}")
        print(f"\nBy category:")
        for cat, count in sorted(stats['category_counts'].items()):
            total_in_cat = len(self.kb['knowledge_categories'].get(cat, []))
            print(f"  {cat:18s}: +{count} (total: {total_in_cat})")
        print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract knowledge from Hugo blog posts")
    parser.add_argument("--repo-path", default=".", help="Root path of the Hugo site")
    parser.add_argument("--post-dir", default="content/posts", help="Posts directory relative to repo")
    parser.add_argument("--config-dir", default="config", help="Config directory relative to repo")

    args = parser.parse_args()

    extractor = PostKnowledgeExtractor(
        repo_path=args.repo_path,
        post_dir=args.post_dir,
        config_dir=args.config_dir
    )

    stats = extractor.extract_from_all_posts()
    extractor.print_summary(stats)
