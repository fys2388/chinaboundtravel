"""P1-GROWTH-19G: Transportation cluster authority audit.

Deterministic, no network. Inspects the content files for the transportation
cluster, computes the internal link graph, coverage flags and commercial
coverage, and writes reports/revenue/TRANSPORTATION_CLUSTER_GRAPH.md.
"""
import csv
import re
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "reports/revenue/TRANSPORTATION_CLUSTER_GRAPH.md"

# cluster nodes: key -> (content_id, file, display, topics covered)
NODES = {
    "transportation_guide": {
        "file": REPO / "content/posts/2026-07-16-china-transportation-complete-guide-trains-subways-taxis-and-more.md",
        "content_id": "cbt-17c6738ffb32",
        "display": "China Transportation Guide",
        "topics": ["train", "metro", "taxi", "didi"],
    },
    "high_speed_rail": {
        "file": REPO / "content/posts/2026-05-25-china-high-speed-rail-how-to-book-tickets.md",
        "content_id": "cbt-cc4549872c92",
        "display": "High-Speed Rail Booking",
        "topics": ["train"],
    },
    "transportation_card": {
        "file": REPO / "content/posts/china-transportation-card-guide.md",
        "content_id": "cbt-55aef784e6aa",
        "display": "China Transportation Card",
        "topics": ["metro", "card", "payment"],
    },
    "airport_transfer": {
        "file": REPO / "content/posts/china-airport-transfer-guide.md",
        "content_id": "cbt-02a3e0d6ed4f",
        "display": "China Airport Transfer",
        "topics": ["airport", "taxi"],
    },
}

COVERAGE_TOPICS = ["train", "metro", "card", "airport", "payment", "apps"]


def node_links(text, target_key):
    """Return number of links from text to the target node's URL."""
    target = NODES[target_key]
    # match both the slug form and any /posts/... slug containing node identity
    slug_hint = target["file"].stem
    candidates = {slug_hint}
    # also match known URL paths
    known = {
        "transportation_guide": "china-transportation-complete-guide-trains-subways-taxis-and-more",
        "high_speed_rail": "china-high-speed-rail-how-to-book-tickets",
        "transportation_card": "china-transportation-card-guide",
        "airport_transfer": "china-airport-transfer-guide",
    }
    candidates.add(known[target_key])
    return sum(text.count("/posts/" + c + "/") for c in candidates)


def build_cluster_audit():
    texts = {k: (n["file"].read_text(encoding="utf-8") if n["file"].exists() else "") for k, n in NODES.items()}

    # adjacency: inbound links per node
    inbound = {}
    for key in NODES:
        total = 0
        for other in NODES:
            if other == key:
                continue
            total += node_links(texts[other], key)
        inbound[key] = total

    # coverage: which topics are covered where
    coverage = {}
    for topic in COVERAGE_TOPICS:
        covered_by = [k for k, n in NODES.items() if topic in n["topics"] or
                      re.search(r"\b" + topic + r"\b", texts[k], re.I)]
        coverage[topic] = covered_by

    orphans = [k for k, n in NODES.items() if inbound[k] == 0]
    commercial = {k: ("comparison-layer" if "affiliate-section" in texts[k] or "affiliate-link" in texts[k] else "none") for k in NODES}

    lines = [
        "# Transportation Cluster Graph (P1-GROWTH-19G)",
        "",
        f"Generated: {date.today().isoformat()}  |  Deterministic audit, no network",
        "",
        "## Nodes",
        "| Node | content_id | Inbound links | Commercial layer |",
        "|---|---|---|---|",
    ]
    for k, n in NODES.items():
        lines.append(f"| {n['display']} | {n['content_id']} | {inbound[k]} | {commercial[k]} |")
    lines += [
        "",
        "## Link graph (directed, A -> B)",
        "| From | To | Links |",
        "|---|---|---|",
    ]
    for src in NODES:
        for dst in NODES:
            if src == dst:
                continue
            cnt = node_links(texts[src], dst)
            if cnt:
                lines.append(f"| {NODES[src]['display']} | {NODES[dst]['display']} | {cnt} |")
    lines += [
        "",
        "## Coverage",
    ]
    for topic in COVERAGE_TOPICS:
        lines.append(f"- {topic}: {', '.join(coverage[topic]) if coverage[topic] else 'UNCOVERED'}")
    lines += [
        "",
        "## Metrics",
        f"- orphan pages (inbound == 0): {len(orphans)} {orphans if orphans else ''}",
        f"- min inbound across cluster: {min(inbound.values()) if inbound else 0}",
        f"- total inbound links: {sum(inbound.values())}",
        "",
        "## Rules",
        "- REV002 CTA frozen; Drive/GA4/affiliate shortcodes unchanged.",
        "- This is an internal measurement, not a Google ranking signal.",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"orphans": orphans, "inbound": inbound, "output": str(OUT)}


if __name__ == "__main__":
    if "--check" in sys.argv:
        result = build_cluster_audit()
        assert result["orphans"] == [], f"orphans found: {result['orphans']}"
        assert min(result["inbound"].values()) >= 1
        assert OUT.exists()
        print(f"OK orphans=0 min_inbound={min(result['inbound'].values())}")
    else:
        result = build_cluster_audit()
        print(f"written {result['output']}")
