"""P0: meta description / summary duplicate concatenation tests.

Root cause: joran_blog_generator.generate_seo_description() padded short
descriptions with the same fixed phrase inside a while loop, so very short
templates got the phrase appended 2-3 times:

    "China National Parks: Zhangjiajie, Jiuzhaigou. practical guide for
     foreign travelers. practical guide for foreign travelers"

These tests pin the audit/fix helpers in scripts/audit_meta_descriptions.py
and verify the generator no longer loops on padding.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

from audit_meta_descriptions import (
    audit_field,
    collapse_consecutive_duplicates,
    find_duplicates,
    parse_front_matter,
)

GENERATOR = REPO_ROOT / "chinaboundtravel_social_bot" / "joran_blog_generator.py"


# ---------- required dedupe cases ----------

def test_duplicate_sentence_collapsed():
    # "A. A. A." -> "A."
    assert collapse_consecutive_duplicates("A. A. A.") == "A."


def test_repeated_phrase_kept_once():
    # consecutive phrase repeat keeps exactly one copy
    text = "practical guide for foreign travelers practical guide for foreign travelers"
    assert collapse_consecutive_duplicates(text) == "practical guide for foreign travelers"


def test_real_world_generator_output_collapsed():
    text = ("China National Parks: Zhangjiajie, Jiuzhaigou. "
            "practical guide for foreign travelers. "
            "practical guide for foreign travelers")
    assert collapse_consecutive_duplicates(text) == (
        "China National Parks: Zhangjiajie, Jiuzhaigou. practical guide for foreign travelers."
    )


def test_triple_phrase_repeat_collapsed_to_one():
    text = ("practical guide for foreign travelers practical guide for foreign travelers "
            "practical guide for foreign travelers")
    assert collapse_consecutive_duplicates(text) == "practical guide for foreign travelers"


# ---------- conservative: hand-written descriptions ----------

def test_non_consecutive_repeat_left_untouched():
    # "A. B. A." is not adjacent; likely intentional, do not fix
    assert collapse_consecutive_duplicates("A. B. A.") == "A. B. A."


def test_handwritten_description_untouched():
    text = "Visit Beijing in spring. Book hotels early. Bring an umbrella."
    assert collapse_consecutive_duplicates(text) == text


# ---------- detection ----------

def test_find_duplicates_detects_sentence_and_phrase():
    assert find_duplicates("A. A. A.") != []
    assert find_duplicates("practical guide for foreign travelers practical guide for foreign travelers") != []


def test_find_duplicates_clean_text_empty():
    assert find_duplicates("Complete Beijing travel guide 2026. Best food and itineraries.") == []


# ---------- audit_field ----------

def test_empty_description_flagged():
    kinds = [k for k, _ in audit_field("description", "   ", "Some Title")]
    assert "empty" in kinds


def test_overlong_description_flagged():
    long_text = "x" * 200
    kinds = [k for k, _ in audit_field("description", long_text, "Some Title")]
    assert "too_long" in kinds


def test_title_duplicate_flagged():
    kinds = [k for k, _ in audit_field("description", "China Travel Guide", "China Travel Guide")]
    assert "title_duplicate" in kinds


# ---------- front matter ----------

def test_parse_front_matter_unquotes():
    fm = """---
title: "China Travel Guide"
description: 'A. A. A.'
summary: "plain value"
---
"""
    values, _ = parse_front_matter(fm)
    assert values["title"] == "China Travel Guide"
    assert values["description"] == "A. A. A."
    assert values["summary"] == "plain value"


# ---------- generator root cause ----------

def test_generator_padding_no_longer_loops():
    src = GENERATOR.read_text(encoding="utf-8")
    # 修复前：while len(description) < 120 里反复追加同一句固定短语，
    # 极短模板会被追加 2-3 次（见本文件 docstring 的复现样例）。
    assert "while len(description) < 120" not in src, "生成器回退到循环填充模式"
    # 2026-09 重构后改为「按预算挑一个合适短语，追加一次即 break」。
    # 因此兜底短语在源码里只能出现一次；出现多次说明又回到了"重复追加"。
    phrase = "Practical guide for foreign travelers"
    assert src.count(phrase) == 1, f"兜底短语出现 {src.count(phrase)} 次，疑似回退到重复追加"
    assert "for extra in (" in src and "break" in src, "预算制单次追加逻辑丢失"
