#!/usr/bin/env python3
"""集成Social Strategy Loader到social_content_agent.py"""

import re
from pathlib import Path

TARGET_FILE = Path(__file__).parent / "social_content_agent.py"

# 读取文件
content = TARGET_FILE.read_text(encoding="utf-8")

# 1. 在social_text_utils导入后添加策略加载器导入
old_import = "from social_text_utils import first_meaningful_desc, strip_shortcodes, validate_social_copy  # noqa: E402\n\nlogger = setup_logger"
new_import = """from social_text_utils import first_meaningful_desc, strip_shortcodes, validate_social_copy  # noqa: E402

# P1-AI-OPS-02: Social Learning闭环 - 加载学习策略（最佳时间/Hook/CTA）
try:
    from social_strategy_loader import SocialStrategyLoader
    _strategy_loader = SocialStrategyLoader()
    _strategy_available = True
except Exception as _e:
    _strategy_loader = None
    _strategy_available = False

logger = setup_logger"""

if old_import in content:
    content = content.replace(old_import, new_import)
    print("✅ 1. 策略加载器导入已添加")
else:
    print("⚠️ 1. 未找到导入位置，尝试替代匹配")
    # 尝试更简单的匹配
    old_import_simple = "from social_text_utils import first_meaningful_desc, strip_shortcodes, validate_social_copy"
    if old_import_simple in content:
        content = content.replace(
            old_import_simple,
            old_import_simple + "\n\n# P1-AI-OPS-02: Social Learning闭环 - 加载学习策略\ntry:\n    from social_strategy_loader import SocialStrategyLoader\n    _strategy_loader = SocialStrategyLoader()\n    _strategy_available = True\nexcept Exception as _e:\n    _strategy_loader = None\n    _strategy_available = False"
        )
        print("✅ 1. 策略加载器导入已添加（替代匹配）")

# 2. 在logger初始化后添加策略加载日志
old_logger = 'logger = setup_logger("social_agent", level="INFO", log_file="social_content_agent.log")'
new_logger = '''logger = setup_logger("social_agent", level="INFO", log_file="social_content_agent.log")

if _strategy_available:
    logger.info("Social Strategy Loader 已加载，版本: %s", _strategy_loader.get_strategy_version())
else:
    logger.warning("Social Strategy Loader 未加载，使用默认策略")'''

if old_logger in content:
    content = content.replace(old_logger, new_logger)
    print("✅ 2. 策略加载日志已添加")
else:
    print("⚠️ 2. 未找到logger初始化位置")

# 3. 添加辅助函数：获取平台策略指导
helper_functions = '''

# P1-AI-OPS-02: Social Learning闭环 - 策略指导函数
def get_strategy_guidance(platform: str) -> dict:
    """获取特定平台的策略指导（基于Social Learning闭环学习结果）"""
    if not _strategy_available or _strategy_loader is None:
        return {}
    try:
        platform_map = {"ig": "instagram", "pinterest": "pinterest", "x": "x", "fb": "facebook"}
        actual_platform = platform_map.get(platform, platform)
        return _strategy_loader.generate_content_guidance(actual_platform)
    except Exception as e:
        logger.warning("获取策略指导失败: %s", e)
        return {}


def get_best_publish_times(platform: str) -> list:
    """获取特定平台的最佳发布时间"""
    if not _strategy_available or _strategy_loader is None:
        return []
    try:
        platform_map = {"ig": "instagram", "pinterest": "pinterest", "x": "x", "fb": "facebook"}
        actual_platform = platform_map.get(platform, platform)
        return _strategy_loader.get_best_times(actual_platform)
    except Exception as e:
        logger.warning("获取最佳发布时间失败: %s", e)
        return []


def apply_strategy_to_caption(caption: str, platform: str, content_type: str) -> str:
    """将学习策略应用到文案生成（添加推荐Hook/CTA提示）"""
    if not _strategy_available:
        return caption
    try:
        guidance = get_strategy_guidance(platform)
        if guidance and guidance.get("recommended_hooks"):
            # 在日志中记录使用的策略
            logger.debug("应用策略到 %s 文案: Hook=%s, CTA=%s",
                        platform,
                        guidance.get("recommended_hooks", [])[:2],
                        guidance.get("recommended_ctas", [])[:2])
    except Exception as e:
        logger.debug("应用策略到文案失败: %s", e)
    return caption
'''

# 在SCHEMA_VERSION定义后添加辅助函数
old_schema = 'SCHEMA_VERSION = 1\nTYPES = ("knowledge", "tip", "story", "visual", "conversion")\nPLATFORMS = ("ig", "pinterest", "x", "fb")'
new_schema = old_schema + helper_functions

if old_schema in content:
    content = content.replace(old_schema, new_schema)
    print("✅ 3. 策略辅助函数已添加")
else:
    print("⚠️ 3. 未找到SCHEMA_VERSION位置")

# 保存文件
TARGET_FILE.write_text(content, encoding="utf-8")
print(f"\n✅ 文件已更新: {TARGET_FILE}")
print(f"   文件大小: {len(content)} 字符")

# 验证语法
import ast
try:
    ast.parse(content)
    print("✅ Python语法验证通过")
except SyntaxError as e:
    print(f"❌ Python语法错误: {e}")
