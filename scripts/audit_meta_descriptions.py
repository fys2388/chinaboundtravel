#!/usr/bin/env python3
"""Audit and fix duplicate/malformed meta descriptions in Hugo posts.

Usage:
    python scripts/audit_meta_descriptions.py --audit
    python scripts/audit_meta_descriptions.py --fix [--dry-run]

Checks content/posts/*.md front matter `description` / `summary`:
  - consecutive duplicate sentences (e.g. "A. A. A.")
  - consecutive repeated phrases (e.g. "practical guide ... practical guide ...")
  - empty description
  - overlong description (> 155 chars, Hugo truncates at 155)
  - description identical to title

--fix only rewrites high-confidence CONSECUTIVE duplicates produced by the AI
generator padding bug. Non-consecutive repeats (e.g. "A. B. A.") and all other
issue types are only reported, so hand-written descriptions are never altered.
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "content" / "posts"

FIELDS = ("description", "summary")
MAX_DESC_LEN = 155  # Hugo truncates meta description to 155 chars
MIN_PHRASE_WORDS = 3
MIN_PHRASE_CHARS = 12


# ---------- front matter helpers ----------

def unquote_yaml(value):
    """Unquote a single-line YAML scalar (double, single or bare)."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value[1:-1]
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    return value


def parse_front_matter(text):
    """Extract {title, description, summary} values and their raw lines."""
    m = re.search(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}, {}
    values, lines = {}, {}
    for line in m.group(1).splitlines():
        mm = re.match(r"^(title|description|summary):\s*(.*)$", line)
        if mm:
            key, raw = mm.group(1), mm.group(2).strip()
            values[key] = unquote_yaml(raw)
            lines[key] = line
    return values, lines


# ---------- duplicate detection ----------

def split_sentences(text):
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def sentence_key(sentence):
    key = re.sub(r"\s+", " ", sentence.lower().strip())
    return key.rstrip(".!?")


def find_consecutive_phrase_duplicates(sentence):
    """Normalized phrases (>=3 words, >=12 chars) repeated consecutively."""
    norm = re.sub(r"[^a-zA-Z0-9\s]", " ", sentence.lower())
    norm = re.sub(r"\s+", " ", norm).strip()
    found = set()
    pattern = r"(\b(?:\w+\s+){%d,}\w+)\s+\1\b" % (MIN_PHRASE_WORDS - 1)
    for m in re.finditer(pattern, norm):
        phrase = m.group(1).strip()
        if len(phrase) >= MIN_PHRASE_CHARS:
            found.add(phrase)
    return sorted(found)


def find_duplicates(text):
    """Return [(kind, sample)] for consecutive sentence/phrase duplicates."""
    issues = []
    sentences = split_sentences(text)
    for i in range(len(sentences) - 1):
        if sentence_key(sentences[i]) == sentence_key(sentences[i + 1]):
            issues.append(("sentence", sentences[i]))
    for sentence in sentences:
        for phrase in find_consecutive_phrase_duplicates(sentence):
            issues.append(("phrase", phrase))
    return issues


def audit_field(field, value, title):
    """Return [(kind, detail)] for one front-matter field."""
    issues = []
    if field == "description":
        if not value.strip():
            issues.append(("empty", "description is empty"))
        if len(value) > MAX_DESC_LEN:
            issues.append(("too_long", "%d chars > %d" % (len(value), MAX_DESC_LEN)))
        if title and _normalize(value) == _normalize(title):
            issues.append(("title_duplicate", "description identical to title"))
    issues.extend(("duplicate", kind + ": " + sample) for kind, sample in find_duplicates(value))
    return issues


def _normalize(text):
    return re.sub(r"\s+", " ", text.strip().lower())


# ---------- fixing (high confidence, consecutive repeats only) ----------

def _collapse_phrase(sentence):
    result = sentence
    for phrase in find_consecutive_phrase_duplicates(sentence):
        words = [re.escape(w) for w in phrase.split()]
        group = r"\b" + r"\s+".join(words) + r"\b[.!?,]?"
        pattern = re.compile(r"(" + group + r")(?:\s+|\s*,\s*)(" + group + r")", re.IGNORECASE)
        result = pattern.sub(lambda m: m.group(1), result)
    return result


def collapse_consecutive_duplicates(text):
    """Collapse only ADJACENT sentence/phrase duplicates (high confidence)."""
    sentences = split_sentences(text)
    out = []
    for sentence in sentences:
        if out and sentence_key(sentence) == sentence_key(out[-1]):
            continue
        out.append(sentence)
    result = " ".join(out).strip()
    # phrase-level collapse, iterate until stable (e.g. triple repeats)
    while True:
        rebuilt = []
        changed = False
        for sentence in split_sentences(result):
            collapsed = _collapse_phrase(sentence)
            if collapsed != sentence:
                changed = True
            rebuilt.append(collapsed)
        result = " ".join(rebuilt).strip()
        if not changed:
            return result


def rewrite_front_matter(path, new_values):
    """Rewrite description/summary lines, preserving quoting and line endings."""
    text = path.read_text(encoding="utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"

    def repl(m):
        key = m.group(1)
        if key in new_values:
            return "%s: %s" % (key, json.dumps(new_values[key], ensure_ascii=False))
        return m.group(0)

    text = re.sub(r"^(title|description|summary):\s*.*$", repl, text, flags=re.M)
    text = text.replace("\r\n", "\n")
    if newline == "\r\n":
        text = text.replace("\n", "\r\n")
    path.write_bytes(text.encode("utf-8"))


# ---------- commands ----------

def audit_posts(content_dir=CONTENT_DIR):
    dup_total = 0
    counters = {"empty": 0, "too_long": 0, "title_duplicate": 0}
    files_with_issues = 0
    for path in sorted(content_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        values, _ = parse_front_matter(text)
        title = values.get("title", "")
        file_issues = []
        for field in FIELDS:
            if field not in values:
                continue
            for kind, detail in audit_field(field, values[field], title):
                file_issues.append((field, kind, detail))
                if kind == "duplicate":
                    dup_total += 1
                elif kind in counters:
                    counters[kind] += 1
        if file_issues:
            files_with_issues += 1
        for field, kind, detail in file_issues:
            print("[%-15s] %s: %s: %s" % (kind, path.name, field, detail))
    print("=" * 70)
    print("files with issues : %d" % files_with_issues)
    print("duplicate issues  : %d" % dup_total)
    print("empty             : %d" % counters["empty"])
    print("too_long          : %d" % counters["too_long"])
    print("title_duplicate   : %d" % counters["title_duplicate"])
    ok = dup_total == 0
    print("P0 duplicate description = %d -> %s" % (dup_total, "PASS" if ok else "FAIL"))
    return 0 if ok else 1


def fix_posts(dry_run=False, content_dir=CONTENT_DIR):
    fixed_files = 0
    fixed_fields = 0
    for path in sorted(content_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        values, _ = parse_front_matter(text)
        new_values = {}
        for field in FIELDS:
            if field not in values:
                continue
            collapsed = collapse_consecutive_duplicates(values[field])
            if collapsed != values[field]:
                new_values[field] = collapsed
        if not new_values:
            continue
        fixed_files += 1
        fixed_fields += len(new_values)
        for field, value in new_values.items():
            print("FIX %s: %s:" % (path.name, field))
            print("  - %s" % values[field])
            print("  + %s" % value)
        if not dry_run:
            rewrite_front_matter(path, new_values)
    print("summary: %d file(s), %d field(s) fixed%s"
          % (fixed_files, fixed_fields, " (dry-run)" if dry_run else ""))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit/fix meta descriptions in content/posts/*.md")
    parser.add_argument("--audit", action="store_true", help="audit only (default)")
    parser.add_argument("--fix", action="store_true", help="fix high-confidence duplicate descriptions")
    parser.add_argument("--dry-run", action="store_true", help="with --fix: preview changes without writing")
    args = parser.parse_args(argv)

    if args.fix:
        return fix_posts(dry_run=args.dry_run)
    return audit_posts()


if __name__ == "__main__":
    sys.exit(main())
