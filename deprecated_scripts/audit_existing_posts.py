# audit_existing_posts.py - ChinaBound Travel Blog Post Auditor & Re-Enhancer
# ===============================================================================
# 用途：遍历 content/posts/ 下所有 .md 文件，主编Agent严审 → 采编Agent针对性重写
#       → 联盟链接补天清洗 → 原样覆盖写回
#
# Usage:
#   python audit_existing_posts.py
#   python audit_existing_posts.py --dry-run
#   python audit_existing_posts.py --limit 5
#   python audit_existing_posts.py --model deepseek
#
# Author: ChinaBound AI Agent | Version: 1.0
# ===============================================================================

import os, re, sys, time, logging, argparse, shutil
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum
import frontmatter

# ============================================================
# SECTION 0: 路径设置
# ============================================================
SCRIPT_DIR = Path(__file__).parent.resolve()
BLOG_ROOT  = Path(os.environ.get("CHINABOUND_BLOG_ROOT", str(SCRIPT_DIR)))

# ============================================================
# SECTION 1: 配置层
# ============================================================

class ModelProvider(Enum):
    DEEPSEEK = "deepseek"
    OPENAI   = "openai"
    CLAUDE   = "claude"
    QWEN     = "qwen"

@dataclass
class LLMConfig:
    provider:    ModelProvider = ModelProvider.DEEPSEEK
    model:       str           = "deepseek-chat"
    base_url:    str           = "https://api.deepseek.com"
    api_key:     str           = ""
    max_tokens:  int           = 400    # 【降本】月预算¥50，进一步降低至400
    temperature: float         = 0.7

@dataclass
class AuditConfig:
    blog_root:        Path      = field(default_factory=lambda: BLOG_ROOT)
    posts_dir:        Path      = field(default_factory=lambda: BLOG_ROOT / "content/posts")
    backup_dir:       Path      = field(default_factory=lambda: BLOG_ROOT / "content/posts/.audit_backup")
    log_file:         Path      = field(default_factory=lambda: BLOG_ROOT / "audit_existing_posts.log")
    max_retries:      int       = 2
    llm:              LLMConfig = field(default_factory=LLMConfig)
    dry_run:          bool      = False
    limit:            int       = 0   # 0 = 无限制

# ============================================================
# SECTION 2: 日志系统
# ============================================================

def setup_logging(log_file: Path = None, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("ChinaBound.Audit")
    logger.setLevel(level); logger.handlers.clear()
    fmt_s = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    fmt_l = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    ch = logging.StreamHandler(sys.stdout); ch.setLevel(logging.INFO); ch.setFormatter(fmt_s); logger.addHandler(ch)
    lf = log_file or BLOG_ROOT / "audit_existing_posts.log"
    fh = logging.FileHandler(str(lf), encoding="utf-8", mode="a")
    fh.setLevel(logging.DEBUG); fh.setFormatter(fmt_l); logger.addHandler(fh)
    return logger

# ============================================================
# SECTION 3: LLM 客户端（与 agent_pipeline.py 相同）
# ============================================================

class LLMClient:
    def __init__(self, config: LLMConfig, logger: logging.Logger):
        self.cfg = config; self.logger = logger; self._client = None; self._init_client()

    def _init_client(self):
        p = self.cfg.provider
        if p in (ModelProvider.DEEPSEEK, ModelProvider.OPENAI, ModelProvider.QWEN):
            from openai import OpenAI
            self._client = OpenAI(api_key=self.cfg.api_key, base_url=self.cfg.base_url, timeout=60.0, max_retries=2)
            self.logger.info(f"LLM: {p.value} model={self.cfg.model} base={self.cfg.base_url}")
        elif p == ModelProvider.CLAUDE:
            import anthropic; self._client = anthropic.Anthropic(api_key=self.cfg.api_key, timeout=60.0)
            self.logger.info(f"LLM: claude model={self.cfg.model}")

    def chat(self, system: str, user: str, temperature: float = None, max_tokens: int = None) -> str:
        # 【预算控制 1/2】前置检查
        try:
            from budget_controller import can_call_api
            if not can_call_api("deepseek-chat"):
                raise Exception("[BUDGET] 预算已用尽，停止所有 API 调用")
        except Exception as e:
            if "[BUDGET]" in str(e):
                raise

        t = temperature or self.cfg.temperature
        m = max_tokens or self.cfg.max_tokens
        # 【降本】硬上限 500 tokens
        m = min(m, 500)

        if self.cfg.provider in (ModelProvider.DEEPSEEK, ModelProvider.OPENAI, ModelProvider.QWEN):
            r = self._client.chat.completions.create(
                model=self.cfg.model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=t, max_tokens=m)
            # 【预算控制 2/2】记录消耗
            self._record_cost(r)
            return r.choices[0].message.content
        elif self.cfg.provider == ModelProvider.CLAUDE:
            r = self._client.messages.create(model=self.cfg.model, system=system,
                messages=[{"role": "user", "content": user}], temperature=t, max_tokens=m)
            return r.content[0].text

    def _record_cost(self, response):
        """记录 API 调用成本（仅 DeepSeek 兼容）"""
        try:
            usage = getattr(response, "usage", None)
            if usage:
                from budget_controller import record_cost
                in_tok = getattr(usage, "prompt_tokens", 0) or 0
                out_tok = getattr(usage, "completion_tokens", 0) or 0
                if in_tok or out_tok:
                    record_cost("deepseek-chat", in_tok, out_tok)
        except Exception:
            pass

# ============================================================
# SECTION 4: 主编 Agent (STEP 1)
# ============================================================

EDITOR_AUDIT_SYSTEM = """You are the Chief Editor of chinaboundtravel.com.

Your job is to strictly review this old China travel post against real-world logistics and our established persona:
Joran (California native married into a Chengdu family, 6 years localized travel experience, witty, direct, American friend tone).

Check for ALL of the following:

1. FACT-CHECK (hallucinations = REJECT):
   - Subway/high-speed rail to Jiuzhaigou, Siguniang Mountain, Western Sichuan, Tibet, remote areas = REJECT
   - Only confirmed real-world transport applies
   - Any factually impossible logistics claims

2. TONE-CHECK (wrong voice = REJECT):
   - "Welcome to beautiful China" = REJECT
   - Official tourism bureau language = REJECT
   - Dry, robotic, or marketing-fluff prose = REJECT
   - Must sound like an American expat friend who has been there

3. MISSING HOOKS (not REJECT, but flag for enhancement):
   - Places where VPN/eSIM warning would be natural
   - Places where hotel/accommodation recommendation fits
   - Places where Klook tour/ticket booking fits
   - Places where car rental/overlanding context fits

First write your detailed review notes (bullet points).
Then output ONE of these exact markers at the VERY END:

   [AUDIT_RESULT: PERFECT]

   [AUDIT_RESULT: NEED_FIX] Issues:
   - <issue 1>
   - <issue 2>
   - etc."""

class EditorAuditor:
    def __init__(self, llm: LLMClient, cfg: AuditConfig, logger: logging.Logger):
        self.llm = llm; self.cfg = cfg; self.logger = logger

    def _extract_result(self, text: str) -> Tuple[str, str, List[str]]:
        """Returns: (result_type, summary, issues_list)"""
        m = re.search(r"\[AUDIT_RESULT:\s*PERFECT\]", text)
        if m:
            return "PERFECT", "", []
        m = re.search(r"\[AUDIT_RESULT:\s*NEED_FIX\]\s*Issues:(.*)", text, re.DOTALL)
        if m:
            raw_issues = m.group(1).strip()
            issues = [l.strip("- ").strip() for l in raw_issues.split("\n") if l.strip()]
            return "NEED_FIX", (issues[0] if issues else "Multiple issues"), issues
        self.logger.warning("[EDITOR] 无法解析AUDIT_RESULT标记，默认NEED_FIX")
        return "NEED_FIX", "Parse error - manual review needed", []

    def audit(self, post: dict) -> Tuple[str, str, List[str]]:
        """Run editor audit on a single post dict with 'front_matter' and 'body' keys."""
        title = post.get("front_matter", {}).get("title", "Untitled")
        body  = post.get("body", "")
        self.logger.info(f"[EDITOR] 开始严审: {title}")
        t0 = time.time()
        response = self.llm.chat(EDITOR_AUDIT_SYSTEM,
            f"Please review this post titled '{title}':\n\n{body}",
            temperature=0.2, max_tokens=400)
        elapsed = time.time() - t0
        result, summary, issues = self._extract_result(response)
        self.logger.info(f"[EDITOR] 审稿{'通过' if result == 'PERFECT' else '需修复'} | 耗时:{elapsed:.1f}s | 摘要:{summary}")
        if issues:
            for iss in issues:
                self.logger.info(f"[EDITOR]   - {iss}")
        return result, response, issues

# ============================================================
# SECTION 5: 采编 Agent (STEP 2)
# ============================================================

REPORTER_REVISION_SYSTEM = """You are Joran, a California native married into a Chengdu family.
You have lived and traveled extensively in China for 6 years. You have personally made every digital and logistic mistake imaginable.

YOUR VOICE: Helpful, witty, straight-talking American friend who has been there, done that.
Start paragraphs with strong first-person hooks like "When I first landed in Chengdu..." or "Trust me, I learned this the hard way...".
NEVER use: marketing fluff, official tourism jargon, "Welcome to beautiful China".
NEVER write from a Chinese domestic perspective.

Your task: Rewrite the old article below, addressing ALL the editor's modification requests.
Keep the article's original meaning, structure, and roughly the same length.
Output ONLY the revised Markdown article. Start immediately with the H1 title.
Do NOT add an front matter - just the article body."""

class ReporterRevisor:
    def __init__(self, llm: LLMClient, cfg: AuditConfig, logger: logging.Logger):
        self.llm = llm; self.cfg = cfg; self.logger = logger

    def revise(self, post: dict, issues: List[str]) -> str:
        title = post.get("front_matter", {}).get("title", "Untitled")
        body  = post.get("body", "")
        issues_text = "\n".join(f"- {iss}" for iss in issues)
        self.logger.info(f"[REPORTER] 开始针对性重写 | issues={len(issues)}")
        t0 = time.time()
        revised = self.llm.chat(REPORTER_REVISION_SYSTEM,
            f"Original article title: {title}\n\n--- ORIGINAL ARTICLE ---\n{body}\n\n--- EDITOR'S MODIFICATION REQUESTS ---\n{issues_text}\n\nPlease rewrite the article addressing all issues above.",
            temperature=0.6, max_tokens=500)
        elapsed = time.time() - t0
        self.logger.info(f"[REPORTER] 重写完成 | 字数:~{len(revised.split())} | 耗时:{elapsed:.1f}s")
        self.logger.debug(f"[REPORTER] 预览:\n{revised[:200]}")
        return revised

# ============================================================
# SECTION 6: 联盟链接清洗 (STEP 3) - 复用 agent_pipeline.py 逻辑
# ============================================================

AFFILIATE_HOOKS = {
    "klook": {
        "keywords": ["panda base","high-speed rail","train ticket","jiuzhaigou",
                     "tour guide","skip-the-line","english guide","day tour","high speed rail"],
        "hook": (
            "\n\n> **Pro Tip:** For booking high-speed rail tickets, English tour guides, or "
            "skip-the-line tickets at the Chengdu Panda Base, "
            "use [Klook](https://klook.tpo.li/ppB4vZQ6) to lock in your slots early!\n\n"
        ),
    },
    "booking": {
        "keywords": ["hotel","stay","accommodation","inn","guesthouse","lodge","hostel","resort"],
        "hook": (
            "\n\n> **Stay Smart:** Looking for comfortable accommodation with great reviews? "
            "Book through our partner for the best rates. (#TP_BOOKING_PLACEHOLDER#)\n\n"
        ),
    },
    "trip": {
        "keywords": ["car rental","road trip","rent a car","prado","4wd","overlanding",
                     "suv","self-drive","overland"],
        "hook": (
            "\n\n> **Joran's Choice:** Planning an overlanding trip to Western Sichuan? "
            "Trip.com is the gold standard for foreigners renting a 4WD SUV in Chengdu. (#TP_TRIP_PLACEHOLDER#)\n\n"
        ),
    },
    "vpn": {
        "keywords": ["vpn","google maps","blocked website","internet access","wifi","wi-fi"],
        "hook": (
            "\n\n> **Stay Connected:** Need reliable internet in China? "
            "Get a VPN that works even in remote areas. (#TP_VPN_PLACEHOLDER#)\n\n"
        ),
    },
}

def inject_affiliate_links(content: str, logger: logging.Logger) -> Tuple[str, Dict]:
    insertions = {"klook": 0, "booking": 0, "trip": 0, "vpn": 0}
    paragraphs = content.split("\n\n"); done = set()
    for i, para in enumerate(paragraphs):
        if i in done: continue
        for brand, data in AFFILIATE_HOOKS.items():
            if any(kw in para.lower() for kw in data["keywords"]):
                paragraphs[i] = para + data["hook"]; done.add(i); insertions[brand] += 1; break
    result = "\n\n".join(paragraphs)
    total = sum(insertions.values())
    logger.info(
        f"[AFFILIATE] 联盟注入 | Klook:{insertions['klook']} "
        f"Booking:{insertions['booking']} Trip:{insertions['trip']} VPN:{insertions['vpn']} | 总计:{total}处")
    return result, insertions

# ============================================================
# SECTION 7: Hugo Front Matter 重建
# ============================================================

def rebuild_front_matter(old_fm: dict, new_body: str) -> str:
    """Rebuild Hugo front matter, updating date and summary from new body."""
    date   = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")
    title  = old_fm.get("title", "Untitled")
    tags   = old_fm.get("tags", ["China Travel", "Travel Tips"])
    cats   = old_fm.get("categories", ["China Travel Guide"])
    # Auto-generate summary from first 160 chars of body
    summary_raw = re.sub(r"^#+\s*", "", new_body).strip()[:160]
    summary = summary_raw.replace('"', '\\"').replace("\n", " ")

    def fmt_list(items):
        if isinstance(items, list):
            return ", ".join(f'"{t}"' for t in items)
        return f'"{items}"'

    return f'''---
title: "{title}"
date: {date}
draft: false
tags: [{fmt_list(tags)}]
categories: [{fmt_list(cats)}]
summary: "{summary}..."
---

'''

def serialize_post(front_matter: dict, body: str) -> str:
    """Serialize front matter + body back to Hugo-compatible markdown string."""
    return rebuild_front_matter(front_matter, body) + body

# ============================================================
# SECTION 8: 文章解析（剥离 Front Matter）
# ============================================================

def parse_post(file_path: Path) -> Optional[dict]:
    """Parse a Hugo .md file, returning dict with front_matter and body."""
    try:
        post = frontmatter.load(file_path)
        fm = dict(post.metadata) if hasattr(post.metadata, "items") else dict(post.metadata)
        # Hugo's date in front matter may be datetime object
        if "date" in fm and hasattr(fm["date"], "strftime"):
            fm["date"] = fm["date"].strftime("%Y-%m-%dT%H:%M:%S+08:00")
        return {"front_matter": fm, "body": post.content, "file_path": file_path}
    except Exception as e:
        return None

# ============================================================
# SECTION 9: 主审计器编排
# ============================================================

class PostAuditor:
    def __init__(self, cfg: AuditConfig, logger: logging.Logger):
        self.cfg = cfg; self.logger = logger
        self.llm  = LLMClient(cfg.llm, logger)
        self.editor   = EditorAuditor(self.llm, cfg, logger)
        self.reporter = ReporterRevisor(self.llm, cfg, logger)

    def scan_posts(self) -> List[Path]:
        """Find all .md files in posts directory."""
        posts = sorted(self.cfg.posts_dir.glob("*.md"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        self.logger.info(f"[SCAN] 发现 {len(posts)} 篇帖子")
        return posts[:self.cfg.limit] if self.cfg.limit else posts

    def audit_single(self, file_path: Path) -> bool:
        """Audit and rewrite a single post. Returns True if modified."""
        title = file_path.name
        self.logger.info("=" * 60)
        self.logger.info(f"[AUDIT] 处理: {title}")
        self.logger.info("=" * 60)

        # Backup original
        self.cfg.backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = self.cfg.backup_dir / file_path.name
        shutil.copy2(str(file_path), str(backup_path))
        self.logger.info(f"[AUDIT] 备份: {backup_path.name}")

        # Parse post
        post_data = parse_post(file_path)
        if not post_data:
            self.logger.error(f"[AUDIT] 解析失败，跳过: {title}"); return False

        original_body = post_data["body"]
        front_matter  = post_data["front_matter"]
        post_title    = front_matter.get("title", title)

        # STEP 1: Editor Audit
        audit_result, editor_response, issues = self.editor.audit(post_data)

        if audit_result == "PERFECT":
            self.logger.info(f"[AUDIT] ✅ 主编判定 PERFECT，直接进入联盟清洗")
            final_body = original_body
        else:
            # STEP 2: Reporter Revise (only if NEED_FIX)
            self.logger.info(f"[AUDIT] 需要修复，调用采编Agent针对性重写")
            final_body = self.reporter.revise(post_data, issues)
            # Fallback if revise returns nothing
            if not final_body or len(final_body.split()) < 100:
                self.logger.warning("[AUDIT] 采编返回过短，保留原文")
                final_body = original_body

        # STEP 3: Affiliate injection (always run)
        final_body, stats = inject_affiliate_links(final_body, self.logger)

        # STEP 4: Write back (preserve front matter)
        if self.cfg.dry_run:
            self.logger.info(f"[AUDIT] ⚠️ DRY-RUN 模式，未实际写入")
            return False

        new_content = serialize_post(front_matter, final_body)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        self.logger.info(f"[AUDIT] ✅ 写回完成: {file_path.name}")
        return True

    def run_all(self) -> Dict[str, int]:
        """Run audit on all posts. Returns stats dict."""
        stats = {"total": 0, "perfect": 0, "fixed": 0, "errors": 0}
        posts = self.scan_posts()
        for path in posts:
            stats["total"] += 1
            try:
                modified = self.audit_single(path)
                if modified:
                    stats["fixed"] += 1
                else:
                    # PERFECT or not modified still counts
                    stats["perfect"] += 1
            except Exception as e:
                self.logger.exception(f"[AUDIT] 处理异常: {path.name}: {e}")
                stats["errors"] += 1
        return stats

# ============================================================
# SECTION 10: CLI 入口
# ============================================================

def resolve_api_key(provider: ModelProvider) -> str:
    if provider == ModelProvider.DEEPSEEK: return os.environ.get("DEEPSEEK_API_KEY", "***REMOVED***")
    elif provider == ModelProvider.OPENAI: return os.environ.get("OPENAI_API_KEY", "")
    elif provider == ModelProvider.CLAUDE: return os.environ.get("ANTHROPIC_API_KEY", "")
    elif provider == ModelProvider.QWEN:    return os.environ.get("DASHSCOPE_API_KEY", "")
    return ""

def main():
    parser = argparse.ArgumentParser(description="ChinaBound Post Auditor & Re-Enhancer")
    parser.add_argument("--dry-run",   action="store_true", help="只审读不写回（测试模式）")
    parser.add_argument("--limit",     type=int, default=1, help="最多处理帖数（默认1，避免浪费token。如需全量显式传入 --limit 0）")
    parser.add_argument("--model",      "-m", choices=["deepseek","openai","claude","qwen"], default="deepseek")
    parser.add_argument("--base-url",   "-b", default="",    help="API Base URL")
    parser.add_argument("--api-key",    help="API Key")
    parser.add_argument("--blog-root",  help="博客根目录")
    args = parser.parse_args()

    provider_map = {"deepseek": ModelProvider.DEEPSEEK, "openai": ModelProvider.OPENAI,
                    "claude": ModelProvider.CLAUDE, "qwen": ModelProvider.QWEN}
    provider = provider_map[args.model]
    default_base = {
        ModelProvider.DEEPSEEK: "https://api.deepseek.com",
        ModelProvider.OPENAI:   "https://api.openai.com/v1",
        ModelProvider.CLAUDE:   "https://api.anthropic.com",
        ModelProvider.QWEN:     "https://dashscope.aliyuncs.com/compatible-mode/v1",
    }[provider]
    model_map = {
        ModelProvider.DEEPSEEK: "deepseek-chat",
        ModelProvider.OPENAI:   "gpt-4o",
        ModelProvider.CLAUDE:   "claude-sonnet-4-20250514",
        ModelProvider.QWEN:     "qwen-plus",
    }[provider]

    llm_cfg = LLMConfig(
        provider=provider, model=model_map,
        base_url=args.base_url or default_base,
        api_key=args.api_key or resolve_api_key(provider),
    )
    blog_root = Path(args.blog_root) if args.blog_root else BLOG_ROOT
    cfg = AuditConfig(
        blog_root=blog_root,
        posts_dir=blog_root / "content/posts",
        backup_dir=blog_root / "content/posts/.audit_backup",
        dry_run=args.dry_run,
        limit=args.limit,
        llm=llm_cfg,
    )

    logger = setup_logging(cfg.log_file)
    logger.info(f"ChinaBound Audit v1.0 启动 | dry={cfg.dry_run} | blog_root={blog_root}")

    if not cfg.llm.api_key:
        logger.error("API Key未设置！请通过 --api-key 或环境变量传递。"); sys.exit(1)

    auditor = PostAuditor(cfg, logger)
    stats = auditor.run_all()

    logger.info("=" * 60)
    logger.info(f"AUDIT COMPLETE | 总:{stats['total']} | 完美:{stats['perfect']} | 修复:{stats['fixed']} | 异常:{stats['errors']}")
    logger.info(f"原始备份目录: {cfg.backup_dir}")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
