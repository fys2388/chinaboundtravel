"""Content dedupe + merge agent (L2).

Scans content/_draft/ for drafts that duplicate already-published posts and
either merges their genuinely-new guidance into the published post, or flags
them for manual review. Deterministic (no LLM).

Classification
--------------
slug_conflict    : draft slug == a published post's slug -> would duplicate a
                   URL. NEVER merged; flagged for human review.
topic_duplicate  : unique slug, but title/slug tokens overlap an existing
                   published post -> merge candidate.
publishable      : no conflict, no overlap -> left untouched (genuinely new).

Merge guardrails (enforced, not advisory)
-----------------------------------------
- policy_gate high-risk topics (visa/safety/insurance/...) are NEVER merged:
  appending policy content to a published article is a modify_facts/
  modify_visa_policy act, which L2 denies.
- Paragraphs already represented in the target are skipped (idempotent).
- Paragraphs containing CJK characters are skipped (site rule: no Chinese
  introduced into article bodies).
- Paragraphs < 60 chars are skipped (no standalone value).
- Drafts are never deleted; merged drafts move to content/_archived/ (Hugo
  ignores "_"-prefixed dirs), so every change is recoverable.
- A .bak copy of the target is written before any edit
  (governance.rollback.require_backup_before_l2_changes).

Modes
-----
  --plan   (default) write reports/content/duplicate_merge_plan.{md,json} only
  --apply              perform the merges, write .bak + rollback manifest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

BLOG_ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = BLOG_ROOT / "content" / "posts"
DRAFTS_DIR = BLOG_ROOT / "content" / "_draft"
ARCHIVE_DIR = BLOG_ROOT / "content" / "_archived"
REPORTS_DIR = BLOG_ROOT / "reports" / "content"
# Rollback backups must NOT live under content/: Hugo copies unrecognized
# extensions in content dirs into public/ as static resources, which leaked
# draft-era markdown to the deployed site. Keep them in reports/ instead.
ROLLBACK_DIR = REPORTS_DIR / "rollback"
sys.path.insert(0, str(BLOG_ROOT / "scripts"))

CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]")
HEADING_RE = re.compile(r"^#{2,3}\s+(.+)$")
# Insert before the last occurrence of one of these trailing sections.
TRAILING_SECTION_RE = re.compile(r"^(##\s+(?:Related|Further|See Also|References)\s|##\s+FAQ\s|##\s+Additional)", re.M)

DEFAULT_MERGE_HEADING = "## Further Guidance"
TITLE_SIM_MIN = 0.28       # char-trigram cosine floor (necessary, not sufficient)
PARA_SIM_MIN = 0.55        # token-Jaccard floor to call a paragraph "already there"
MIN_PARA_CHARS = 60

# Title cosine alone can't separate true duplicates from unrelated posts
# (measured on this repo: etiquette true-dup 0.383 vs gastronomic false-pos
# 0.366). Require at least one shared entity term as well.
CITIES = {
    "shanghai", "beijing", "chengdu", "guangzhou", "hangzhou", "shenzhen",
    "sichuan", "yunnan", "chongqing", "changsha", "xian", "kunming", "dali",
    "harbin", "dalian", "zhengzhou", "wuhan", "nanjing", "qingdao", "xiamen",
    "suzhou", "zhangjiajie", "lhasa", "guilin", "yangshuo", "tianshin",
    "tianshan", "hainan", "hefei", "luoyang", "qingdao",
}
TOPICS = {
    "visa", "transport", "food", "etiquette", "safety", "nightlife", "train",
    "hotel", "itinerary", "culture", "cultural", "business", "shopping",
    "payment", "alipay", "wechat", "esim", "photography", "family", "solo",
    "budget", "work", "remote", "visa-free", "visa_free", "neighborhood",
    "neighborhoods", "street-food", "bargaining", "panda",
}
ENTITY_TERMS = CITIES | TOPICS

# Intro/outro paragraphs make no sense grafted onto a published article that
# already has its own intro and conclusion. Excluded from merges.
INTRO_OUTRO_RE = re.compile(
    r"\b(this guide|this article|this post|in this article|in this post|"
    r"let'?s start|let'?s dive|in conclusion|to sum up|one final note|"
    r"finally,|here'?s what|here is what|here'?s everything|get ready for|"
    r"planning a trip to china|in this final|throughout this|we'?ll cover|"
    r"we will cover|this week|in the following|welcome to)\b",
    re.I,
)


def entities(text: str) -> set[str]:
    low = text.lower()
    return {t for t in ENTITY_TERMS if re.search(rf"\b{re.escape(t)}\b", low)}


@dataclass
class DraftAssessment:
    draft_file: str
    draft_slug: str
    kind: str = ""                    # slug_conflict | topic_duplicate | publishable                       # slug_conflict | topic_duplicate | publishable
    match_file: str = ""            # published post it overlaps ("" if none)
    match_slug: str = ""
    sim: float = 0.0
    policy_blocked: bool = False
    policy_reason: str = ""
    paras_total: int = 0
    paras_mergeable: int = 0
    paragraphs: list = field(default_factory=list)
    action: str = "none"


def read_fm(text: str) -> tuple[str, str, str, str]:
    """Return (frontmatter, body, title, slug)."""
    text = text.lstrip("\ufeff")
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return "", text, "", ""
    fm = m.group(1)
    body = text[m.end() :]

    def grab(key: str) -> str:
        mm = re.search(rf"^{key}:\s*['\"]?([^'\"\n]+)", fm, re.M)
        return mm.group(1).strip().strip('"') if mm else ""

    return fm, body, grab("title"), grab("slug")
    return fm, body, title, slug


def slug_from_name(name: str) -> str:
    s = re.sub(r"^[\d\-]+\s*", "", name)              # strip date prefix
    s = re.sub(r"-attempt\d+$", "", s)                # strip generator suffix
    s = re.sub(r"\.md$", "", s)
    return s


def tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]{3,}", text.lower())
    stop = {"the", "and", "for", "with", "how", "your", "from", "this", "that",
            "are", "was", "you", "our", "all", "can", "its", "into", "china",
            "chinese", "guide", "travel", "tips", "tips", "2026", "2025", "2024",
            "best", "top", "top-rated", "new", "complete", "full", "part", "about",
            "what", "where", "when", "which", "have", "has", "not", "but", "than"}
    return {w for w in words if w not in stop}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def trigram_sim(a: str, b: str) -> float:
    """Char-trigram cosine similarity.

    Token Jaccard on titles is brittle here: many draft slugs are noise
    (e.g. "china-just-made-it-way-easier-to-visit-my-mother-i"), which drags
    title+slug Jaccard below the threshold even when titles are near-identical.
    Char trigrams survive word order and extra words.
    """
    def sh(s: str) -> set[str]:
        s = re.sub(r"[^a-z0-9 ]", " ", s.lower())
        s = re.sub(r"\s+", " ", s).strip()
        return {s[i : i + 3] for i in range(max(len(s) - 2, 0))} if len(s) >= 3 else set()

    sa, sb = sh(a), sh(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / ((len(sa) * len(sb)) ** 0.5)


def paragraphs_of(body: str) -> list[str]:
    """Body -> prose paragraphs worth considering for merge.

    Skips headings, lists, tables, blockquotes, code, shortcodes, images and
    anything under MIN_PARA_CHARS.
    """
    out = []
    for block in re.split(r"\n\s*\n", body):
        b = block.strip()
        if not b:
            continue
        if b.startswith("#"):                       # heading
            continue
        if b.startswith(("{", "[Image", "|", "<", "!", ">", "`", "-", "*")):
            continue
        if re.match(r"^\d+\.\s", b):                # ordered list
            continue
        if len(b) < MIN_PARA_CHARS:
            continue
        out.append(b)
    return out


def load_policy_gate() -> set[str]:
    """High-risk categories from ai_governance.json (empty set if unavailable)."""
    gov = BLOG_ROOT / "config" / "ai_governance.json"
    if not gov.exists():
        return set()
    return set(json.loads(gov.read_text(encoding="utf-8")).get("policy_gate", {}).get("high_risk_categories", []))


def policy_hit(text: str, categories: set[str]) -> str:
    """Return the matched high-risk category, or "" if none."""
    low = text.lower()
    for cat in sorted(categories):
        words = {"visa": ["visa", "visas", "passport", "immigration"],
                 "safety": ["safety", "danger", "crime", "safe for tourists"],
                 "insurance": ["insurance", "policy claim"],
                 "law": ["law", "legal", "regulation", "regulations"],
                 "financial": ["price", "pricing", "refund", "fee", "cost"],
                 "pricing": ["price", "pricing"],
                 "immigration": ["visa", "immigration"],
                 "partner_terms": ["partner", "terms"]}.get(cat, [cat])
        for w in words:
            if re.search(rf"\b{re.escape(w)}\b", low):
                return cat
    return ""


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def scan() -> tuple[list[DraftAssessment], dict]:
    policy = load_policy_gate()
    published: dict[str, Path] = {}
    pub_titles: dict[Path, str] = {}
    for p in sorted(POSTS_DIR.glob("*.md")):
        _, _, title, slug = read_fm(p.read_text(encoding="utf-8"))
        published[slug or slug_from_name(p.name)] = p
        pub_titles[p] = title or slug or p.stem

    results: list[DraftAssessment] = []
    for d in sorted(DRAFTS_DIR.glob("*.md")):
        text = d.read_text(encoding="utf-8")
        fm, body, title, slug = read_fm(text)
        dslug = slug or slug_from_name(d.name)
        dlabel = title or dslug
        a = DraftAssessment(draft_file=str(d.relative_to(BLOG_ROOT)), draft_slug=dslug)
        a.paras_total = len(paragraphs_of(body))

        if dslug in published:
            a.kind = "slug_conflict"
            a.match_file = str(published[dslug].relative_to(BLOG_ROOT))
            a.match_slug = dslug
            a.sim = 1.0
            a.action = "flag: slug collides with a published post; publishing would duplicate a URL. Merge manually or retire."
            results.append(a)
            continue

        best, best_sim = None, 0.0
        for p, ptitle in pub_titles.items():
            s = trigram_sim(dlabel, ptitle)
            if s > best_sim:
                best, best_sim = p, s
        a.sim = round(best_sim, 3)
        d_ent = entities(dlabel)
        if best is not None and best_sim >= TITLE_SIM_MIN and (d_ent & entities(pub_titles[best])):
            a.kind = "topic_duplicate"
            a.match_file = str(best.relative_to(BLOG_ROOT))
            a.match_slug = next((k for k, v in published.items() if v == best), best.name)

            # Policy gate at the TARGET level: never merge into a policy article.
            if policy_hit(pub_titles[best], policy):
                a.action = "skip: target is a policy-gated article; not merged"
                a.policy_blocked = True
                a.policy_reason = f"target article is {policy_hit(pub_titles[best], policy)}"
                results.append(a)
                continue

            target_body = read_fm(best.read_text(encoding="utf-8"))[1]
            paras = paragraphs_of(body)
            kept = []
            for para in paras:
                if policy_hit(para, policy):
                    a.policy_blocked = True
                    a.policy_reason = ", ".join(sorted({policy_hit(q, policy) for q in paras if policy_hit(q, policy)}))
                    continue
                if CJK_RE.search(para):
                    continue
                if INTRO_OUTRO_RE.search(para):
                    continue
                if jaccard(tokens(para), tokens(target_body)) >= PARA_SIM_MIN:
                    continue
                if any(p.lower() == para.lower() for p in kept):
                    continue
                kept.append(para)
            a.paragraphs = kept
            a.paras_mergeable = len(kept)
            if a.policy_blocked and not kept:
                a.action = "skip: all content is policy-gated"
            elif kept:
                a.action = "merge"
            else:
                a.action = "skip: nothing new to add"
        else:
            a.kind = "publishable"
            a.action = "none: no conflict, leave for normal publishing"
        results.append(a)

    stats = {
        "drafts": len(results),
        "slug_conflict": sum(1 for r in results if r.kind == "slug_conflict"),
        "topic_duplicate": sum(1 for r in results if r.kind == "topic_duplicate"),
        "publishable": sum(1 for r in results if r.kind == "publishable"),
        "mergeable_paras": sum(r.paras_mergeable for r in results),
    }
    return results, stats


def render_plan(results, stats) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    L = [f"# Duplicate Draft Merge Plan\n", f"Generated {now} by `scripts/content_dedup_merge.py` (deterministic, no LLM).\n",
         f"**Dry run — no files modified.** Re-run with `--apply` to merge.\n",
         f"- Drafts scanned: **{stats['drafts']}**",
         f"- `slug_conflict` (never merge): **{stats['slug_conflict']}**",
         f"- `topic_duplicate`: **{stats['topic_duplicate']}**",
         f"- `publishable` (no conflict): **{stats['publishable']}**",
         f"- Mergeable paragraphs total: **{stats['mergeable_paras']}**\n"]
    for r in results:
        L.append(f"## `{Path(r.draft_file).name}`")
        L.append(f"- kind: `{r.kind}`  sim={r.sim}")
        if r.match_file:
            L.append(f"- target: `{r.match_file}`")
        if r.policy_reason:
            L.append(f"- ⚠️ policy-gated topic(s): {r.policy_reason} — never merged")
        L.append(f"- paragraphs: {r.paras_total} total, {r.paras_mergeable} mergeable")
        L.append(f"- action: {r.action}")
        for i, p in enumerate(r.paragraphs, 1):
            L.append(f"\n> **{i}.** {p}\n")
        L.append("")
    return "\n".join(L)


def apply(results) -> list[dict]:
    from ai_governance import check_kill_switch, require_permission

    is_ok, reason = check_kill_switch()
    if not is_ok:
        raise SystemExit(f"KILL SWITCH ACTIVE: {reason}")
    require_permission("content", "merge_content")

    RECORDS: list[dict] = []
    for r in results:
        if r.action != "merge" or not r.match_file:
            continue
        src = BLOG_ROOT / r.draft_file
        dst = BLOG_ROOT / r.match_file
        require_permission("content", "deduplicate")

        before = dst.read_text(encoding="utf-8")
        ROLLBACK_DIR.mkdir(parents=True, exist_ok=True)
        backup = ROLLBACK_DIR / (dst.name + ".bak-" + datetime.now().strftime("%Y%m%d%H%M%S"))
        shutil.copy2(dst, backup)

        body = read_fm(before)[1]
        existing = {p.strip() for p in body.split("\n\n")}
        additions = [p for p in r.paragraphs if p.strip() not in existing]
        if not additions:
            backup.unlink()
            continue

        m = TRAILING_SECTION_RE.search(body)
        if m:
            new_body = (body[: m.start()].rstrip() + "\n\n" + DEFAULT_MERGE_HEADING + "\n\n"
                        + "\n\n".join(additions) + "\n\n" + body[m.start() :])
        else:
            new_body = body.rstrip() + "\n\n" + DEFAULT_MERGE_HEADING + "\n\n" + "\n\n".join(additions) + "\n\n"

        # Rebuild as frontmatter + new body (frontmatter is never rewritten).
        head = re.match(r"^---\s*\n(.*?)\n---\s*\n", before, re.DOTALL)
        after = (head.group(0) if head else "") + new_body
        dst.write_text(after, encoding="utf-8")

        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(ARCHIVE_DIR / src.name))

        RECORDS.append({
            "draft": r.draft_file,
            "target": r.match_file,
            "target_backup": backup.relative_to(BLOG_ROOT).as_posix(),
            "draft_archived_to": f"content/_archived/{src.name}",
            "paragraphs_added": len(additions),
            "target_sha256_before": sha256(backup),
            "target_sha256_after": sha256(dst),
            "rollback": f"copy {backup.relative_to(BLOG_ROOT).as_posix()} back over {r.match_file}",
        })
    return RECORDS


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="perform merges (default is plan-only)")
    ap.add_argument("--plan-only", action="store_true")
    args = ap.parse_args()

    results, stats = scan()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d")

    plan_md = REPORTS_DIR / f"duplicate_merge_plan_{stamp}.md"
    plan_json = REPORTS_DIR / f"duplicate_merge_plan_{stamp}.json"
    plan_md.write_text(render_plan(results, stats), encoding="utf-8")
    plan_json.write_text(json.dumps({"stats": stats, "drafts": [asdict(r) for r in results]}, ensure_ascii=False, indent=2), encoding="utf-8")
    (REPORTS_DIR / "duplicate_merge_plan.md").write_text(plan_md.read_text(encoding="utf-8"), encoding="utf-8")
    (REPORTS_DIR / "duplicate_merge_plan.json").write_text(plan_json.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"[plan] wrote {plan_md.relative_to(BLOG_ROOT)}")
    print(f"[plan] {json.dumps(stats)}")

    if not args.apply:
        print("[plan] dry run — re-run with --apply to merge")
        return 0

    records = apply(results)
    manifest = REPORTS_DIR / f"duplicate_merge_manifest_{stamp}.json"
    manifest.write_text(json.dumps({"applied_at": datetime.now(timezone.utc).isoformat(), "records": records}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[apply] merged {len(records)} drafts; manifest {manifest.relative_to(BLOG_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
