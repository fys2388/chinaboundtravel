"""
auto_bomber.py - ChinaBound Travel Blog Automated Publishing System
Author: ChinaBound AI Agent
Version: 2.0 - Enhanced with paragraph-by-paragraph affiliate injection
Description: Automatically processes AI-generated markdown drafts, inserts affiliate links,
             adds Hugo Front Matter, and publishes to content/posts/
"""

import os
import re
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import hashlib

# ============== CONFIGURATION ==============
class Config:
    # Paths
    AI_DRAFTS_DIR = Path("ai_drafts")
    OUTPUT_POSTS_DIR = Path("content/posts")
    BACKUP_DIR = Path("content/posts/.processed_backup")
    ARCHIVE_DIR = Path("content/posts/.archived")

    # Affiliate Links
    KLOOK_LINK = "https://klook.tpo.li/ppB4vZQ6"
    BOOKING_PLACEHOLDER = "#TP_BOOKING_PLACEHOLDER#"
    TRIP_PLACEHOLDER = "#TP_TRIP_PLACEHOLDER#"
    VPN_PLACEHOLDER = "#TP_VPN_PLACEHOLDER#"

    # Keywords for affiliate insertion
    KLOOK_KEYWORDS = [
        r"panda\s*base", r"high.?speed\s*rail", r"train\s*ticket",
        r"jiuzhaigou", r"hot\s*spring", r"english\s*guide",
        r"skip.?the.?line", r"day\s*tour", r"chartered\s*car",
        r"panda base", r"tour guide"
    ]

    BOOKING_KEYWORDS = [
        r"\bhotel\b", r"\bstay\b", r"\baccommodation\b",
        r"\binn\b", r"\bguesthouse\b", r"\blodge\b",
        r"\bhostel\b", r"\bresort\b"
    ]

    TRIP_KEYWORDS = [
        r"car\s*rental", r"road\s*trip", r"rent\s*a\s*car",
        r"\bprado\b", r"\b4wd\b", r"\bsuv\b",
        r"drive\s*to", r"overland", r"self.?drive",
        r"overlanding"
    ]

    VPN_KEYWORDS = [
        r"\bvpn\b", r"google\s*maps", r"blocked\s*website",
        r"internet\s*access", r"wifi\s*voucher"
    ]

    # Default Front Matter
    DEFAULT_TAGS = ["China Travel", "Sichuan Guide", "Travel Tips"]
    DEFAULT_CATEGORY = "Guides"
    DEFAULT_DRAFT = False

# ============== LOGGING SETUP ==============
def setup_logging() -> logging.Logger:
    """Configure logging for the automation system"""
    logger = logging.getLogger("AutoBomber")
    logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_format)

    # File handler
    file_handler = logging.FileHandler("auto_bomber.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s | %(pathname)s:%(lineno)d"
    )
    file_handler.setFormatter(file_format)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

# ============== FRONT MATTER GENERATOR ==============
def generate_front_matter(title: str, tags: List[str] = None, category: str = None) -> str:
    """Generate Hugo-compatible Front Matter"""
    if tags is None:
        tags = Config.DEFAULT_TAGS
    if category is None:
        category = Config.DEFAULT_CATEGORY

    # Clean title: remove markdown headers, extra spaces
    clean_title = re.sub(r"^#+\s*", "", title).strip()
    clean_title = re.sub(r"\s+", " ", clean_title)

    # Format date
    date_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")

    # Format tags
    tags_str = ", ".join([f'"{tag}"' for tag in tags])

    front_matter = f"""---
title: "{clean_title}"
date: {date_str}
draft: {str(Config.DEFAULT_DRAFT).lower()}
tags: [{tags_str}]
categories: ["{category}"]
summary: "{clean_title[:200]}..."
---

"""

    return front_matter

# ============== CONTENT PROCESSOR ==============
class ContentProcessor:
    """
    Processes markdown content and inserts affiliate links using paragraph-by-paragraph logic.
    If a paragraph contains target keywords, append the hook AFTER that paragraph.
    Only one affiliate link per paragraph to prevent over-marketing.
    """

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.stats = {
            "files_processed": 0,
            "klook_inserted": 0,
            "booking_inserted": 0,
            "trip_inserted": 0,
            "vpn_inserted": 0
        }

    def inject_affiliate_links(self, content: str) -> Tuple[str, Dict]:
        """
        Inject affiliate links using paragraph-by-paragraph logic.
        If a paragraph contains target keywords, append the hook AFTER that paragraph.
        Only one affiliate link per paragraph to prevent over-marketing.
        """
        insertions = {"klook": 0, "booking": 0, "trip": 0, "vpn": 0}

        # Affiliate hooks configuration with precise copy from user
        affiliate_hooks = {
            "klook": {
                "keywords": [
                    "panda base", "high-speed rail", "train ticket", "jiuzhaigou",
                    "tour guide", "skip-the-line", "english guide", "day tour",
                    "high speed rail"
                ],
                "hook": '\n\n> **Pro Tip:** For booking China High-Speed Rail tickets, English tour guides, or securing skip-the-line tickets for the Chengdu Panda Base, use this [Klook](https://klook.tpo.li/ppB4vZQ6) to lock in your slots early!\n\n'
            },
            "trip": {
                "keywords": [
                    "car rental", "road trip", "rent a car", "prado", "4wd",
                    "overlanding", "suv", "self-drive", "self drive", "overland"
                ],
                "hook": '\n\n> **Joran\'s Choice:** Planning an overlanding trip to Western Sichuan? For renting a decent 4WD SUV in Chengdu, Trip.com is the gold standard for foreigners. (#TP_TRIP_PLACEHOLDER#)\n\n'
            },
            "booking": {
                "keywords": [
                    "hotel", "stay", "accommodation", "inn", "guesthouse",
                    "lodge", "hostel", "resort"
                ],
                "hook": '\n\n> **Stay Smart:** Looking for comfortable accommodation with great reviews? Book through our partner for best rates. (#TP_BOOKING_PLACEHOLDER#)\n\n'
            },
            "vpn": {
                "keywords": [
                    "vpn", "google maps", "blocked website", "internet access", "wifi"
                ],
                "hook": '\n\n> **Stay Connected:** Need reliable internet in China? Get a VPN that works great even in remote areas. (#TP_VPN_PLACEHOLDER#)\n\n'
            }
        }

        # Split into paragraphs
        paragraphs = content.split('\n\n')
        processed_indices = set()  # Track paragraphs that already have an affiliate link

        for i, para in enumerate(paragraphs):
            # Skip if this paragraph already has an insertion
            if i in processed_indices:
                continue

            # Check each affiliate brand
            for brand, data in affiliate_hooks.items():
                if any(kw in para.lower() for kw in data["keywords"]):
                    # Insert hook AFTER this paragraph
                    paragraphs[i] = para + data["hook"]
                    processed_indices.add(i)  # Mark as processed
                    insertions[brand] += 1

                    # Log the insertion
                    self.logger.debug(f"Inserted {brand} hook after paragraph {i}")

                    # One brand per paragraph only
                    break

        return '\n\n'.join(paragraphs), insertions

    def process_content(self, content: str) -> Tuple[str, Dict]:
        """Process content and insert affiliate links"""
        # Use the paragraph-by-paragraph injection logic
        processed_content, insertions = self.inject_affiliate_links(content)

        # Update stats
        self.stats["klook_inserted"] += insertions["klook"]
        self.stats["booking_inserted"] += insertions["booking"]
        self.stats["trip_inserted"] += insertions["trip"]
        self.stats["vpn_inserted"] += insertions["vpn"]

        return processed_content, insertions

    def get_stats(self) -> Dict:
        """Return processing statistics"""
        return self.stats.copy()

# ============== FILE PROCESSOR ==============
class FileProcessor:
    """Handles file operations for the automation system"""

    def __init__(self, logger: logging.Logger, processor: ContentProcessor):
        self.logger = logger
        self.processor = processor
        self.processed_files = []

    def _ensure_directories(self):
        """Ensure all required directories exist"""
        for directory in [Config.AI_DRAFTS_DIR, Config.OUTPUT_POSTS_DIR,
                         Config.BACKUP_DIR, Config.ARCHIVE_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Directory verified: {directory}")

    def _generate_filename(self, title: str) -> str:
        """Generate SEO-friendly filename from title"""
        # Remove markdown headers
        clean_title = re.sub(r"^#+\s*", "", title).strip()

        # Convert to lowercase, replace spaces with hyphens
        filename = re.sub(r"[^a-zA-Z0-9\s-]", "", clean_title)
        filename = filename.lower().replace(" ", "-")

        # Limit length and add date prefix
        filename = filename[:60]
        date_prefix = datetime.now().strftime("%Y-%m-%d")
        filename = f"{date_prefix}-{filename}.md"

        return filename

    def _backup_file(self, filepath: Path):
        """Create backup of processed file"""
        if Config.BACKUP_DIR.exists():
            backup_name = Config.BACKUP_DIR / filepath.name
            shutil.copy2(filepath, backup_name)
            self.logger.debug(f"Backup created: {backup_name}")

    def process_file(self, filepath: Path) -> bool:
        """Process a single markdown file"""
        try:
            self.logger.info(f"Processing: {filepath.name}")

            # Read content
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content.strip():
                self.logger.warning(f"Empty file skipped: {filepath.name}")
                return False

            # Extract title from first heading or line
            title_match = re.search(r"^#+\s*(.+)$", content, re.MULTILINE)
            title = title_match.group(1) if title_match else content.split('\n')[0][:100]

            # Process content (insert affiliate links)
            processed_content, insertions = self.processor.process_content(content)

            # Generate front matter
            front_matter = generate_front_matter(title)

            # Combine front matter with content
            final_content = front_matter + processed_content

            # Generate output filename
            output_filename = self._generate_filename(title)
            output_path = Config.OUTPUT_POSTS_DIR / output_filename

            # Write to output directory
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_content)

            self.logger.info(
                f"✅ Published: {output_filename} "
                f"(Klook: {insertions['klook']}, Booking: {insertions['booking']}, "
                f"Trip: {insertions['trip']}, VPN: {insertions['vpn']})"
            )

            # Backup original
            self._backup_file(filepath)

            # Move original to archive
            archive_path = Config.ARCHIVE_DIR / filepath.name
            shutil.move(str(filepath), str(archive_path))

            self.processed_files.append(output_filename)
            self.processor.stats["files_processed"] += 1

            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to process {filepath.name}: {str(e)}")
            return False

    def scan_and_process(self) -> List[str]:
        """Scan drafts directory and process all files"""
        self._ensure_directories()

        if not Config.AI_DRAFTS_DIR.exists():
            self.logger.warning(f"Drafts directory not found: {Config.AI_DRAFTS_DIR}")
            return []

        md_files = list(Config.AI_DRAFTS_DIR.glob("*.md"))

        if not md_files:
            self.logger.info("No new drafts to process.")
            return []

        self.logger.info(f"Found {len(md_files)} draft(s) to process.")

        for filepath in md_files:
            self.process_file(filepath)

        return self.processed_files

# ============== MAIN ORCHESTRATOR ==============
class AutoBomber:
    """Main orchestrator for the automated publishing system"""

    def __init__(self):
        self.logger = setup_logging()
        self.processor = ContentProcessor(self.logger)
        self.file_processor = FileProcessor(self.logger, self.processor)

    def run_once(self) -> Dict:
        """Run a single processing cycle"""
        self.logger.info("=" * 50)
        self.logger.info("🚀 AutoBomber started - Processing AI drafts...")
        self.logger.info("=" * 50)

        processed = self.file_processor.scan_and_process()

        stats = self.processor.get_stats()

        self.logger.info("=" * 50)
        self.logger.info("📊 Processing Complete!")
        self.logger.info(f"   Files processed: {stats['files_processed']}")
        self.logger.info(f"   Klook links inserted: {stats['klook_inserted']}")
        self.logger.info(f"   Booking placeholders: {stats['booking_inserted']}")
        self.logger.info(f"   Trip placeholders: {stats['trip_inserted']}")
        self.logger.info(f"   VPN placeholders: {stats['vpn_inserted']}")
        self.logger.info("=" * 50)

        return stats

    def run_watch_mode(self, interval: int = 60):
        """Run in watch mode, processing new files periodically"""
        import time

        self.logger.info(f"👁️ Watch mode activated - Checking every {interval} seconds...")
        self.logger.info("Press Ctrl+C to stop.")

        try:
            while True:
                self.run_once()
                self.logger.info(f"⏰ Next check in {interval} seconds...\n")
                time.sleep(interval)
        except KeyboardInterrupt:
            self.logger.info("\n🛑 Watch mode stopped by user.")

# ============== CLI INTERFACE ==============
def main():
    """Command-line interface"""
    import argparse

    parser = argparse.ArgumentParser(
        description="ChinaBound AutoBomber - Automated Travel Blog Publisher"
    )
    parser.add_argument(
        "--watch", "-w",
        action="store_true",
        help="Run in watch mode (continuous monitoring)"
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=60,
        help="Check interval in seconds for watch mode (default: 60)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (default)"
    )

    args = parser.parse_args()

    bomber = AutoBomber()

    if args.watch:
        bomber.run_watch_mode(interval=args.interval)
    else:
        # Default: run once
        stats = bomber.run_once()
        if stats["files_processed"] > 0:
            print(f"\n✅ Successfully processed {stats['files_processed']} file(s)!")
        else:
            print("\n📭 No files to process. Add markdown files to 'ai_drafts/' directory.")

if __name__ == "__main__":
    main()
