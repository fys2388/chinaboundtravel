"""
agent_pipeline.py - ChinaBound Travel Blog AI Agent Publishing Pipeline
双Agent漏斗机制：采编Agent -> 主编Agent -> 联盟清洗 -> Hugo发布
Version: 1.0
"""

import os, re, sys, time, logging, argparse, shutil
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict
from dataclasses import dataclass, field
from enum import Enum

SCRIPT_DIR = Path(__file__).parent.resolve()
BLOG_ROOT  = Path(os.environ.get("CHINABOUND_BLOG_ROOT", str(SCRIPT_DIR)))

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
    max_tokens:  int           = 500    # 【降本】月预算¥50，进一步降低至500
    temperature: float         = 0.7

@dataclass
class PipelineConfig:
    blog_root:         Path       = field(default_factory=lambda: BLOG_ROOT)
    topic_pool_file:   Path       = field(default_factory=lambda: BLOG_ROOT / "topic_pool.txt")
    ai_drafts_dir:     Path       = field(default_factory=lambda: BLOG_ROOT / "ai_drafts")
    posts_dir:         Path       = field(default_factory=lambda: BLOG_ROOT / "content/posts")
    backup_dir:        Path       = field(default_factory=lambda: BLOG_ROOT / "content/posts/.processed_backup")
    archive_dir:       Path       = field(default_factory=lambda: BLOG_ROOT / "content/posts/.archived")
    max_retries:       int        = 2
    target_word_count:  int        = 1500
    llm:               LLMConfig  = field(default_factory=LLMConfig)

def setup_logging(log_file: Path = None, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("ChinaBound.Pipeline")
    logger.setLevel(level); logger.handlers.clear()
    fmt_s = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    fmt_l = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    ch = logging.StreamHandler(sys.stdout); ch.setLevel(logging.INFO); ch.setFormatter(fmt_s); logger.addHandler(ch)
    lf = log_file or (BLOG_ROOT / "agent_pipeline.log")
    fh = logging.FileHandler(str(lf), encoding="utf-8", mode="a")
    fh.setLevel(logging.DEBUG); fh.setFormatter(fmt_l); logger.addHandler(fh)
    return logger

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
            # 如果模块导入失败，继续执行（不中断流程）
            pass

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
            r = self._client.messages.create(
                model=self.cfg.model, system=system,
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

REPORTER_SYSTEM = """You are Joran, a California native married into a Chengdu family.
You have lived and traveled extensively in China for 6 years.

YOUR VOICE: Helpful, witty, straight-talking American friend who has been there, done that.
Start paragraphs with strong first-person hooks like "When I first landed in Chengdu..." or "Trust me, I learned this the hard way...".
NEVER use marketing fluff, official tourism jargon, or "Welcome to beautiful China".
NEVER write from a Chinese domestic perspective.

Write a ~1500-word English travel guide in Markdown based on the topic given.
Requirements: H1 title + 3-5 H2 sections, personal stories in 3+ places,
a "What I Wish I Knew Before" callout blockquote, "Joran's Take" ending paragraph.
Output ONLY the article. No meta-commentary. Start immediately with the H1 title."""

class ReporterAgent:
    def __init__(self, llm: LLMClient, cfg: PipelineConfig, logger: logging.Logger):
        self.llm = llm; self.cfg = cfg; self.logger = logger

    def generate(self, topic: str) -> str:
        self.logger.info(f"[STEP-1] 采编Agent开始生成: {topic}")
        t0 = time.time()
        article = self.llm.chat(
            REPORTER_SYSTEM,
            f"Write a ~{self.cfg.target_word_count}-word travel guide about: {topic}\n\nStart immediately with the H1 title.",
            temperature=0.75, max_tokens=500)
        elapsed = time.time() - t0
        self.logger.info(f"[STEP-1] 采编完成 | 字数:~{len(article.split())} | 耗时:{elapsed:.1f}s")
        self.logger.debug(f"[STEP-1] 预览:\n{article[:200]}")
        return article

EDITOR_SYSTEM = """You are Editor-in-Chief of ChinaBound Travel Blog - codename LAO WANG.
58-year-old veteran, zero tolerance for bullshit.

DEAD-SEEKING RULES (any violation = REJECT):

RULE 1 - TRANSPORT ANTI-HALLUCINATION:
China has vast rural areas with NO subway or direct high-speed rail.
REJECT if draft says subway/HSR goes to Jiuzhaigou, Siguniang Mountain, Western Sichuan, or other remote areas.
Only confirmed HSR routes are valid (Beijing-Shanghai, Chengdu-Chongqing, etc.).

RULE 2 - VOICE & PERSONA:
The article MUST be from American expat (Joran) perspective. Reject if:
  - "Welcome to beautiful China" or official tourism language
  - Chinese domestic perspective ("As a Chinese..." etc.)
  - Marketing fluff: "world-class", "breathtaking", "unforgettable experience"

RULE 3 - FACTS:
Visa-free rules, hotel booking, internet must match 2026 Western traveler reality.

First write your review notes (bullets). Then output ONE of these at the VERY END:

   [REVIEW_RESULT: PASS]

   [REVIEW_RESULT: REJECT] Reason: <one-line summary>"""

EDITOR_REVISION = """The Editor-in-Chief REJECTED the draft.
REJECTION REASON: {reason}
Rewrite the article addressing this issue. Keep everything good. Stay in Joran's voice.
Output ONLY the revised Markdown. Start immediately with the H1 title."""

class EditorAgent:
    def __init__(self, llm: LLMClient, cfg: PipelineConfig, logger: logging.Logger):
        self.llm = llm; self.cfg = cfg; self.logger = logger

    def _extract_result(self, text: str):
        m = re.search(r"\[REVIEW_RESULT:\s*REJECT\]\s*Reason:\s*(.+)", text)
        if m: return False, m.group(1).strip()
        if re.search(r"\[REVIEW_RESULT:\s*PASS\]", text): return True, ""
        self.logger.warning("[STEP-2] 无法解析REVIEW_RESULT标记，默认PASS")
        return True, ""

    def review(self, article: str) -> Tuple[bool, str, int]:
        current = article
        for attempt in range(self.cfg.max_retries + 1):
            self.logger.info(f"[STEP-2] 主编审稿 | 轮次:{attempt+1}/{self.cfg.max_retries+1}")
            t0 = time.time()
            response = self.llm.chat(
                EDITOR_SYSTEM,
                f"Please review this article:\n\n{current}",
                temperature=0.2, max_tokens=400)
            elapsed = time.time() - t0
            is_pass, reason = self._extract_result(response)
            self.logger.info(f"[STEP-2] 审稿{'通过' if is_pass else '驳回'} | 耗时:{elapsed:.1f}s | 原因:{reason or 'N/A'}")
            if is_pass: return True, response, attempt
            if attempt >= self.cfg.max_retries:
                self.logger.error("[STEP-2] 超过最大重试次数，强制通过（需人工复核）")
                return True, response, attempt
            self.logger.info(f"[STEP-2] 主编驳回，重新生成... reason={reason}")
            t0 = time.time()
            current = self.llm.chat(
                EDITOR_REVISION.format(reason=reason), "",
                temperature=0.6, max_tokens=500)
            self.logger.info(f"[STEP-2] 重新生成完成 | 耗时:{time.time()-t0:.1f}s")
        return True, current, attempt

AFFILIATE_HOOKS = {
    "klook": {
        "keywords": ["panda base","high-speed rail","train ticket","jiuzhaigou","tour guide","skip-the-line","english guide","day tour","high speed rail"],
        "hook": "\n\n> **Pro Tip:** For booking high-speed rail tickets, English tour guides, or skip-the-line tickets at the Chengdu Panda Base, use [Klook](https://klook.tpo.li/ppB4vZQ6) to lock in your slots early!\n\n",
    },
    "booking": {
        "keywords": ["hotel","stay","accommodation","inn","guesthouse","lodge","hostel","resort"],
        "hook": "\n\n> **Stay Smart:** Looking for comfortable accommodation with great reviews? Book through our partner for the best rates. (#TP_BOOKING_PLACEHOLDER#)\n\n",
    },
    "trip": {
        "keywords": ["car rental","road trip","rent a car","prado","4wd","overlanding","suv","self-drive","overland"],
        "hook": "\n\n> **Joran's Choice:** Planning an overlanding trip to Western Sichuan? Trip.com is the gold standard for foreigners renting a 4WD SUV in Chengdu. (#TP_TRIP_PLACEHOLDER#)\n\n",
    },
    "vpn": {
        "keywords": ["vpn","google maps","blocked website","internet access","wifi","wi-fi"],
        "hook": "\n\n> **Stay Connected:** Need reliable internet in China? Get a VPN that works even in remote areas. (#TP_VPN_PLACEHOLDER#)\n\n",
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
    logger.info(f"[STEP-3] 联盟注入 | Klook:{insertions['klook']} Booking:{insertions['booking']} Trip:{insertions['trip']} VPN:{insertions['vpn']} | 总计:{total}处")
    return result, insertions

def generate_front_matter(title: str, tags: List = None, category: str = "China Travel Guide") -> str:
    clean = re.sub(r"^#+\s*", "", title).strip()[:200]
    date  = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")
    tags  = tags or ["China Travel", "Travel Tips"]
    tags_str = ", ".join('"' + t + '"' for t in tags)
    return "---\ntitle: \"" + clean + "\"\ndate: " + date + "\ndraft: false\ntags: [" + tags_str + "]\ncategories: [\"" + category + "\"]\nsummary: \"" + clean + "...\"\n---\n\n\n"

def slugify(title: str) -> str:
    t = re.sub(r"^#+\s*", "", title).strip()
    s = re.sub(r"[^a-zA-Z0-9 \-]", "", t).lower().replace(" ", "-")
    return datetime.now().strftime("%Y-%m-%d") + "-" + s[:60] + ".md"

class HugoPublisher:
    def __init__(self, cfg: PipelineConfig, logger: logging.Logger):
        self.cfg = cfg; self.logger = logger

    def publish(self, article: str, title: str) -> Path:
        for d in [self.cfg.ai_drafts_dir, self.cfg.posts_dir, self.cfg.backup_dir, self.cfg.archive_dir]:
            d.mkdir(parents=True, exist_ok=True)
        clean = re.sub(r"^#+\s*", "", title).strip()
        filename = slugify(clean)
        draft_path = self.cfg.ai_drafts_dir / filename
        with open(draft_path, "w", encoding="utf-8") as f: f.write(article)
        self.logger.info(f"[STEP-4] 草稿保存: {draft_path.name}")
        processed, stats = inject_affiliate_links(article, self.logger)
        final = generate_front_matter(clean) + processed
        out_path = self.cfg.posts_dir / filename
        with open(out_path, "w", encoding="utf-8") as f: f.write(final)
        shutil.move(str(draft_path), str(self.cfg.archive_dir / filename))
        self.logger.info(f"[STEP-4] Hugo发布完成: content/posts/{filename}")
        return out_path

def load_topic_pool(path: Path, logger: logging.Logger) -> List[str]:
    if not path.exists():
        logger.warning(f"[TOPIC] 选题池不存在: {path}"); path.write_text("", encoding="utf-8"); return []
    lines = [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    logger.info(f"[TOPIC] 读取选题池: {len(lines)} 个选题")
    return lines

def pop_topic(path: Path, topic: str, logger: logging.Logger):
    lines = path.read_text(encoding="utf-8").splitlines()
    new_lines = [l for l in lines if l.strip() and l.strip() != topic]
    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    logger.info(f"[TOPIC] 选题已移除: {topic[:50]}")

class Pipeline:
    def __init__(self, cfg: PipelineConfig, logger: logging.Logger):
        self.cfg = cfg; self.logger = logger
        self.llm = LLMClient(cfg.llm, logger)
        self.reporter = ReporterAgent(self.llm, cfg, logger)
        self.editor   = EditorAgent(self.llm, cfg, logger)
        self.publisher = HugoPublisher(cfg, logger)

    def run_topic(self, topic: str) -> bool:
        self.logger.info("=" * 60)
        self.logger.info(f"[PIPELINE] 开始处理选题: {topic}")
        self.logger.info("=" * 60)
        try:
            article = self.reporter.generate(topic)
            if not article or len(article.split()) < 200:
                self.logger.error("[PIPELINE] 采编返回内容过短，终止"); return False
            is_pass, editor_response, attempt = self.editor.review(article)
            if not is_pass:
                self.logger.warning("[PIPELINE] 主编连续驳回，强制保存（需人工审核）")
            final_article = article
            if "[REVIEW_RESULT: PASS]" in editor_response:
                parts = editor_response.split("[REVIEW_RESULT: PASS]")
                if len(parts) > 1 and len(parts[1].strip()) > 200:
                    final_article = parts[1].strip()
            out_path = self.publisher.publish(final_article, topic)
            self.logger.info("=" * 60)
            self.logger.info(f"[PIPELINE] 全部完成 | 输出: {out_path.name}")
            self.logger.info("=" * 60)
            return True
        except Exception as e:
            self.logger.exception(f"[PIPELINE] 流水线异常: {e}"); return False

    def run_all(self, watch: bool = False, interval: int = 300):
        while True:
            topics = load_topic_pool(self.cfg.topic_pool_file, self.logger)
            if not topics:
                self.logger.info("[PIPELINE] 选题池为空，结束")
                if not watch: break
                self.logger.info(f"[PIPELINE] {interval}秒后重新检查..."); time.sleep(interval); continue
            topic = topics[0]
            ok = self.run_topic(topic)
            if ok: pop_topic(self.cfg.topic_pool_file, topic, self.logger)
            if not watch: break

def resolve_api_key(provider: ModelProvider) -> str:
    if provider == ModelProvider.DEEPSEEK: return os.environ.get("DEEPSEEK_API_KEY", "***REMOVED***")
    elif provider == ModelProvider.OPENAI: return os.environ.get("OPENAI_API_KEY", "")
    elif provider == ModelProvider.CLAUDE: return os.environ.get("ANTHROPIC_API_KEY", "")
    elif provider == ModelProvider.QWEN:    return os.environ.get("DASHSCOPE_API_KEY", "")
    return ""

def main():
    p = argparse.ArgumentParser(description="ChinaBound AI Agent Publishing Pipeline")
    p.add_argument("--topic",   "-t", help="指定单个选题运行")
    p.add_argument("--watch",   "-w", action="store_true", help="监听模式（持续处理新选题）")
    p.add_argument("--interval","-i", type=int, default=300, help="监听模式轮询间隔（秒，默认300）")
    p.add_argument("--model",   "-m", choices=["deepseek","openai","claude","qwen"], default="deepseek", help="LLM模型供应商")
    p.add_argument("--base-url","-b", default="", help="API Base URL（覆盖默认）")
    p.add_argument("--api-key", help="API Key（覆盖环境变量和默认值）")
    p.add_argument("--blog-root", help="博客根目录（默认脚本所在目录）")
    args = p.parse_args()

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
    cfg = PipelineConfig(
        blog_root=blog_root,
        topic_pool_file=blog_root / "topic_pool.txt",
        ai_drafts_dir=blog_root / "ai_drafts",
        posts_dir=blog_root / "content/posts",
        max_retries=2, llm=llm_cfg,
    )
    logger = setup_logging(blog_root / "agent_pipeline.log")
    logger.info(f"ChinaBound Pipeline v1.0 启动 | provider={provider.value} | blog_root={blog_root}")
    if not cfg.llm.api_key:
        logger.error("API Key未设置！请通过 --api-key 或环境变量传递。"); sys.exit(1)
    pipeline = Pipeline(cfg, logger)
    if args.topic:
        ok = pipeline.run_topic(args.topic); sys.exit(0 if ok else 1)
    else:
        pipeline.run_all(watch=args.watch, interval=args.interval)

if __name__ == "__main__":
    main()
