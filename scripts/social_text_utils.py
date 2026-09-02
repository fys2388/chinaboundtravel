#!/usr/bin/env python3
"""
社媒文案文本清理与质量校验公共工具（P1-OPS-04 修复）。

供 content_rotator.py / chinaboundtravel_social_bot/social_publisher.py /
social_content_agent.py 共用，解决已上线的 4 类问题：
  1. SHORTCODE_LEAK   —— 正文里的 Hugo shortcode `{{< ... >}}` 泄漏到社媒文案
  2. TEXT_GARBLE      —— "Dreaming of exploring Can Foreigners Use, Pay, China?" 语序错乱
  3. META_TRUNCATION  —— 描述在句子中间被硬截断
  4. TITLE_DUP        —— title + description 拼接造成标题视觉重复

用法：
    from social_text_utils import clean_social_text, extract_destination,
                                   ensure_article_url, validate_social_copy
"""
import re

# ---------------------------------------------------------------
# 1. 文本剥离（shortcode / HTML / markdown 符号）
# ---------------------------------------------------------------

# Hugo shortcode：{{< soft-recommend partner="..." ... >}} ... {{< /soft-recommend >}}
SHORTCODE_BLOCK_RE = re.compile(r"\{\{<\s*/?[^>}]*>.*?\}\}", re.DOTALL)
SHORTCODE_INLINE_RE = re.compile(r"\{\{<\s*/?[^>}]*>\}\}")
SHORTCODE_COMMENT_RE = re.compile(r"\{\{/\*.*?\*/\}\}", re.DOTALL)
HTML_TAG_RE = re.compile(r"<[^>]+>")
MARKDOWN_SYMBOL_RE = re.compile(r"[#>*_`\[\]\(\)]")
MULTISPACE_RE = re.compile(r"\s+")


def strip_shortcodes(text: str) -> str:
    """剥离 Hugo shortcode（含成对块与行内形式）与 Hugo 注释。"""
    if not text:
        return ""
    text = SHORTCODE_BLOCK_RE.sub(" ", text)
    text = SHORTCODE_INLINE_RE.sub(" ", text)
    text = SHORTCODE_COMMENT_RE.sub(" ", text)
    return text


def clean_social_text(text: str) -> str:
    """把原始 markdown 文本清理成适合社媒的纯文本：
    shortcode、HTML 标签、markdown 符号全部剥离，压缩空白。"""
    if not text:
        return ""
    text = strip_shortcodes(text)
    text = HTML_TAG_RE.sub(" ", text)
    text = MARKDOWN_SYMBOL_RE.sub(" ", text)
    text = text.replace("|", " ")
    text = MULTISPACE_RE.sub(" ", text).strip()
    return text


def trim_leading_title(text: str, title: str) -> str:
    """若文本以标题开头（常见于 description 直接取自正文第一段），
    去掉标题前缀，避免 title+desc 拼接时视觉重复。
    兼容标题在 clean 后丢失括号/标点的情况（如 '(2026 Guide)' -> '2026 Guide'）。"""
    if not text or not title:
        return text
    t = title.strip()
    t_no_paren = re.sub(r"[()\[\]]", "", t)
    candidates = [
        t,
        t_no_paren,
        t.rstrip(".:!? "),
        t_no_paren.rstrip(".:!? "),
        t.replace("—", "-"),
        t_no_paren.replace("—", "-"),
    ]
    for c in candidates:
        if c and len(c) >= 8 and text.startswith(c):
            text = text[len(c):].lstrip(" .:—,，。")
            break
    return text


def truncate_at_sentence(text: str, max_chars: int) -> str:
    """在句子边界截断文本（优先 . ! ? 后跟空白；其次单词边界），
    避免 'I almost'、'Dos and Don.' 这类半句残文。
    若句子边界截断结果过短（< 40% 长度），退回单词边界以保留更多内容。"""
    if len(text) <= max_chars:
        return text
    window = text[: max_chars]
    ends = [m.end() for m in re.finditer(r"[.!?]\s+", window)]
    if ends:
        cut = window[: ends[-1]].rstrip()
        if len(cut) >= max_chars * 0.4:
            return cut
    # 窗口内无句子边界：向后扩展到下一个句子边界，避免单词边界截断产生残句
    rest = text[max_chars:]
    m = re.search(r"[.!?](?:\s+|$)", rest)
    if m:
        cut = (text[: max_chars] + rest[: m.end()]).rstrip()
        if len(cut) <= max_chars * 2:
            return cut
    cut = window.rsplit(" ", 1)[0]
    return cut if cut else window


def first_meaningful_desc(body_clean: str, title: str, max_len: int = 200) -> str:
    """从清理后的正文提取可用描述：
    - 剥离 shortcode/HTML/markdown 符号
    - 去掉以标题开头的前缀
    - 句子边界截断
    - 空则回退到标题本身
    """
    if not body_clean:
        return title or ""
    desc = clean_social_text(body_clean)
    desc = trim_leading_title(desc, title)
    desc = truncate_at_sentence(desc, max_len).strip(" .")
    if len(desc) < 40:
        desc = clean_social_text(title)
    return desc


# ---------------------------------------------------------------
# 2. 目的地提取（修复 TEXT_GARBLE）
# ---------------------------------------------------------------

# 中国目的地/地区白名单（长名称在前，按标题出现顺序匹配）
CHINA_PLACES = [
    "Inner Mongolia", "Hong Kong", "Great Wall", "West Lake", "Terracotta Army",
    "Forbidden City", "Zhangjiajie", "Shangri-La", "Chongqing", "Hangzhou",
    "Guangzhou", "Shenzhen", "Shanghai", "Chengdu", "Kunming", "Guilin",
    "Beijing", "Harbin", "Dunhuang", "Lanzhou", "Urumqi", "Yunnan",
    "Sichuan", "Xinjiang", "Macau", "Lhasa", "Tibet", "Xi'an", "Xian",
    "Nanjing", "Suzhou", "Wuhan", "Dalian", "Qingdao", "Xiamen",
    "Changsha", "Tianjin", "Hainan", "China",
]

# 标题中的功能性/疑问词，绝不当作目的地
NON_DEST_WORDS = {
    "a", "an", "and", "or", "in", "of", "for", "with", "to", "from", "at",
    "on", "by", "the", "your", "our", "how", "why", "what", "where", "when",
    "which", "who", "whom", "whose", "can", "could", "would", "should", "do",
    "does", "did", "is", "are", "was", "were", "use", "using", "used", "pay",
    "see", "book", "guide", "guides", "ultimate", "complete", "best", "top",
    "first", "first-timers", "first-timer", "foreigners", "foreigner",
    "international", "travelers", "travellers", "traveler", "traveller",
    "travel", "trip", "visa", "visas", "need", "need-to-know", "like", "local",
    "locals", "survival", "must", "know", "before", "after", "during", "via",
    "tourist", "tourists", "beginner", "beginners", "guidebook", "tips",
}


def _find_place_in_title(title: str) -> str:
    """按标题中出现位置返回第一个中国目的地（出现最早者优先）。"""
    low = title.lower()
    best = None
    best_pos = len(title) + 1
    for place in CHINA_PLACES:
        m = re.search(r"(?<![a-z])" + re.escape(place.lower()) + r"(?![a-z])", low)
        if m and m.start() < best_pos:
            best, best_pos = place, m.start()
    return best or ""


def _find_capital_phrase(title: str) -> str:
    """兜底：取第一个不在停用词表、且含中国地名关键词的大写短语。"""
    words = re.findall(r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b", title)
    for w in words:
        first = w.split()[0].lower()
        if first in NON_DEST_WORDS or len(w) < 3:
            continue
        # 仅当短语本身含已知地名词时采纳（避免 'Pack'/'Use' 这类非地名）
        if any(
            re.search(r"(?<![a-z])" + re.escape(p.lower()) + r"(?![a-z])", w.lower())
            for p in CHINA_PLACES
        ):
            return w
    return ""


def extract_destination(title: str) -> str:
    """从标题提取用于 'Dreaming of exploring {X}?' 的目的地。
    优先级：标题中出现最早的中国目的地白名单词 > 'China'。
    绝不截取标题前几个大写词（修复 'Can Foreigners Use, Pay, China?' 语序错乱）。"""
    if not title:
        return "China"
    place = _find_place_in_title(title)
    if place:
        return place
    phrase = _find_capital_phrase(title)
    return phrase if phrase else "China"


# ---------------------------------------------------------------
# 3. URL 保证
# ---------------------------------------------------------------

def ensure_article_url(url: str, slug: str = "", site_domain: str = "chinaboundtravel.com") -> str:
    """保证文章 URL 非空：为空时用 slug 构造站点 URL。"""
    u = (url or "").strip()
    if u.startswith("http://") or u.startswith("https://"):
        return u
    if u.startswith("/"):
        return f"https://www.{site_domain}{u}"
    if slug:
        return f"https://www.{site_domain}/posts/{slug}/"
    return f"https://www.{site_domain}/"


# ---------------------------------------------------------------
# 5. 社媒配图过滤（发布规则：禁止人物头像、禁止抽象图）
# ---------------------------------------------------------------

# 人物/头像特征（alt 文本或图片 URL/文件名命中即弃用）
HUMAN_HINT_RE = re.compile(
    r"\b(person|people|face|portrait|human|humans|figure|figures|crowd|man\b|men\b|woman|women|"
    r"child|children|kid\b|kids|selfie|tourist|tourists|traveler|traveller|backpacker|"
    r"vendor|vendors|seller|sellers|hawker|stallholder|waiter|waitress|chef|cook\b|barista|"
    r"guide\b|driver\b|musician|performer|monk|nun\b|silhouette|headshot|avatar|"
    r"group\s+photo|smiling)\b|"
    r"(人像|人物|人头|面孔|人群|游客|旅人|背包客|自拍|合照|头像|小贩|摊主|厨师|服务员|向导)",
    re.IGNORECASE,
)

# 抽象/非写实特征（命中即弃用：抽象艺术、插画、卡通、3D 渲染、图案、极简、概念图等）
ABSTRACT_HINT_RE = re.compile(
    r"\b(abstract|abstraction|gradient|geometric|illustration|cartoon|vector|"
    r"minimalist|minimalism|artistic|artwork|digital\s+art|3d\s+render|3d\s+model|"
    r"render|texture|pattern|graphic|concept\s+art|conceptual|surreal|watercolor|"
    r"painting|sketch|drawing|doodle|icon\s+set|placeholder|mockup|wireframe|"
    r"colorful\s+background|blurred\s+background)\b|"
    r"(抽象|插画|卡通|矢量|极简|概念图|示意图|渲染图|水彩|素描|涂鸦|纹理|图案)",
    re.IGNORECASE,
)

# 图片生成提示词中的负面关键词（用于从 pollinations URL 反查）
PROMPT_NEGATIVE_RE = re.compile(
    r"(negative=|[?&]prompt=[^&]*%2C\s*(person|people|human|abstract))",
    re.IGNORECASE,
)


# 否定前缀：出现这些表达时，其后的"人物词"不算人物（如 "no people"、"without people"）
HUMAN_NEGATION_RE = re.compile(
    r"\b(no|without|zero|none|nobody|not|no\.?\s*|w/o)\s+(people|persons|person|faces|face|"
    r"humans|human|figures|figure|crowd|tourists|tourist|man|men|woman|women|child|children)",
    re.IGNORECASE,
)


def _human_free_hay(alt: str, url: str) -> str:
    """剥离否定表达与 pollinations 'negative=' 参数后的人物检测文本。
    - 'no people' / 'without people' 不应被判为含人物
    - URL 中 'negative=person,woman,child' 是生成图的排除词，同样不应判为含人物
    """
    hay = f"{alt or ''} {url or ''}"
    hay = HUMAN_NEGATION_RE.sub(" ", hay)
    hay = re.sub(r"[?&]negative=[^&\s]*", " ", hay)
    return hay


def _abstract_hay(alt: str, url: str) -> str:
    """抽象检测文本：同样忽略 URL 的 negative 参数（'no abstract' 排除词不误判）。"""
    hay = f"{alt or ''} {url or ''}"
    return re.sub(r"[?&]negative=[^&\s]*", " ", hay)


def is_acceptable_social_image(alt: str = "", url: str = "") -> bool:
    """判断一张图是否可用于社媒配图：
    - 禁止人物/头像（alt 或 URL 含人物特征 → False；'no people' 等否定表达不误判）
    - 禁止抽象/非写实图（alt 或 URL 含抽象特征 → False；negative 排除词不误判）
    两者都不命中 → True（可用于配图）。"""
    if HUMAN_HINT_RE.search(_human_free_hay(alt, url)):
        return False
    if ABSTRACT_HINT_RE.search(_abstract_hay(alt, url)):
        return False
    return True


def image_rejection_reason(alt: str = "", url: str = "") -> str:
    """返回弃图原因（'human' / 'abstract' / ''）。"""
    if HUMAN_HINT_RE.search(_human_free_hay(alt, url)):
        return "human"
    if ABSTRACT_HINT_RE.search(_abstract_hay(alt, url)):
        return "abstract"
    return ""


# ---------------------------------------------------------------
# 4. 发布前校验（lint）
# ---------------------------------------------------------------

SHORTCODE_HINT_RE = re.compile(r"\{\{<")
EMPTY_CTA_RE = re.compile(
    r"(Read more|Full article|Full breakdown|Your ultimate guide is here|Full guide|Save this guide)\s*[:：]?\s*($|[#@])",
    re.IGNORECASE,
)
PROMPT_HINT_RE = re.compile(
    r"(Ultra-detailed professional travel photography|no watermark|8k resolution|ZERO people|negative=)",
    re.IGNORECASE,
)
LEGACY_PERSONA_RE = re.compile(
    r"(\bHey,?\s+[A-Z][a-z]+(?:\s+Here)?\b|you're in [A-Z]|Like a Local\b|I'll be honest with you)",
    re.IGNORECASE,
)
# frontmatter/YAML 键值残留（正文里出现 'title: "..."' / 'description: "..."' 等）
YAML_LEAK_RE = re.compile(
    r"\b(title|description|summary|slug|author|date|lastmod|content_id)\s*:\s*[\"']",
    re.IGNORECASE,
)


def validate_social_copy(text: str, title: str = "", url: str = "") -> list:
    """校验一条社媒文案，返回问题列表（空列表 = 通过）。

    检查项：
      - shortcode / 模板语法残留
      - CTA 占位符后链接为空
      - 图片生成提示词泄漏
      - 旧第一人称人设残留
      - 标题在文案中重复出现两次
      - URL 缺失
    """
    problems = []
    if not text:
        problems.append("EMPTY_COPY: 文案为空")
        return problems

    if SHORTCODE_HINT_RE.search(text):
        problems.append("SHORTCODE_LEAK: 正文残留 {{< ... >}}")

    if YAML_LEAK_RE.search(text):
        problems.append("YAML_LEAK: 正文残留 frontmatter/YAML 键值（title:/description:）")

    if EMPTY_CTA_RE.search(text):
        problems.append("EMPTY_CTA_LINK: 'Read more/Full article' 等占位符后无链接")

    if PROMPT_HINT_RE.search(text):
        problems.append("PROMPT_LEAK: 图片生成提示词泄漏到正文")

    if title and LEGACY_PERSONA_RE.search(text):
        # 剔除标题本身后重新检测，避免标题里的 'Like a Local' 等误报
        rest = re.sub(re.escape(title), "", text, flags=re.IGNORECASE)
        if LEGACY_PERSONA_RE.search(rest):
            problems.append("LEGACY_PERSONA: 旧第一人称人设残留")

    if url and url not in text:
        problems.append("URL_MISSING: 文案中未包含文章链接")

    if title and len(title) >= 12:
        # 标题出现 >=3 次视为拼接重复（容忍一次 desc 首句自然引用）
        count = len(re.findall(re.escape(title), text, flags=re.IGNORECASE))
        if count >= 3:
            problems.append("TITLE_DUP: 标题在文案中重复出现")

    # 半句截断检测：以 '...' 结尾或最后一个词是介词/连接词
    trailing = re.search(r"(\b(?:the|and|or|of|to|for|with|in|on|at|is|are|was|were|almost|just|like|you)\s*)$", text, re.IGNORECASE)
    if trailing:
        problems.append("META_TRUNCATION: 文案以 '...' 或介词/连接词结尾，疑似截断")

    return problems
