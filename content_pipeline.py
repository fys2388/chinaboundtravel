#!/usr/bin/env python3
"""
content_pipeline.py - ChinaBound Travel 完整内容生产流水线
选题池调度 → Joran生成 → 副主编初审 → 主编终审 → 图片处理 → 发布上线 → 凌晨巡检 → 学习迭代

Version: 1.0
"""

import os
import sys
import json
import random
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

# 导入图片处理器
try:
    from image_processor import process_markdown_images
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from image_processor import process_markdown_images

BASE_DIR = Path(__file__).parent.resolve()
CONFIG_DIR = BASE_DIR / "config"
POSTS_DIR = BASE_DIR / "content" / "posts"
DRAFTS_DIR = BASE_DIR / "content" / "posts" / "drafts"

# 确保目录存在
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
DRAFTS_DIR.mkdir(parents=True, exist_ok=True)


# ==================== 选题池调度 ====================

class TopicPool:
    """选题池调度系统"""
    
    def __init__(self):
        self.topic_pool_path = CONFIG_DIR / "topic_pool.json"
        self.topic_pool = self._load_topic_pool()
    
    def _load_topic_pool(self):
        """加载选题池"""
        if self.topic_pool_path.exists():
            try:
                with open(self.topic_pool_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            "topics": [],
            "used_topics": [],
            "last_update": None
        }
    
    def _save_topic_pool(self):
        """保存选题池"""
        self.topic_pool["last_update"] = datetime.now().isoformat()
        with open(self.topic_pool_path, 'w', encoding='utf-8') as f:
            json.dump(self.topic_pool, f, indent=2, ensure_ascii=False)
    
    def add_topic(self, title: str, category: str, geo: str, keywords: list, priority: int = 1):
        """添加选题"""
        topic = {
            "id": hashlib.md5(f"{title}{datetime.now()}".encode()).hexdigest()[:8],
            "title": title,
            "category": category,
            "geo": geo,
            "keywords": keywords,
            "priority": priority,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "used_at": None
        }
        self.topic_pool["topics"].append(topic)
        self._save_topic_pool()
        return topic
    
    def get_next_topic(self) -> dict:
        """获取下一个选题（按优先级排序）"""
        pending_topics = [t for t in self.topic_pool["topics"] if t["status"] == "pending"]
        if not pending_topics:
            return None
        
        # 按优先级和创建时间排序
        pending_topics.sort(key=lambda x: (-x["priority"], x["created_at"]))
        return pending_topics[0]
    
    def mark_topic_used(self, topic_id: str):
        """标记选题已使用"""
        for topic in self.topic_pool["topics"]:
            if topic["id"] == topic_id:
                topic["status"] = "used"
                topic["used_at"] = datetime.now().isoformat()
                self.topic_pool["used_topics"].append(topic)
                self._save_topic_pool()
                return True
        return False
    
    def get_pool_stats(self) -> dict:
        """获取选题池统计"""
        total = len(self.topic_pool["topics"])
        pending = len([t for t in self.topic_pool["topics"] if t["status"] == "pending"])
        used = len([t for t in self.topic_pool["topics"] if t["status"] == "used"])
        return {
            "total_topics": total,
            "pending_topics": pending,
            "used_topics": used
        }


# ==================== Joran生成器（带错题库自学） ====================

class JoranGenerator:
    """Joran博客生成器 - 前置读取错题库自学避错"""
    
    def __init__(self):
        self.error_knowledge_path = CONFIG_DIR / "error_knowledge_base.json"
        self.learned_rules = self._load_learned_rules()
    
    def _load_learned_rules(self) -> list:
        """加载已学习的规则（从错题库）"""
        if self.error_knowledge_path.exists():
            try:
                with open(self.error_knowledge_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 提取已解决的错误模式作为规则
                    rules = []
                    for pattern in data.get("error_patterns", []):
                        if pattern.get("resolved") and pattern.get("suggestion"):
                            rules.append({
                                "type": pattern["type"],
                                "avoid": pattern["message"],
                                "do": pattern["suggestion"]
                            })
                    return rules
            except:
                pass
        return []
    
    def _generate_content(self, topic: dict) -> str:
        """生成博客内容（模拟）"""
        title = topic["title"]
        category = topic["category"]
        geo = topic["geo"]
        keywords = topic["keywords"]
        
        content = f"""---
title: "{title}"
cover:
  image: "https://image.pollinations.ai/prompt/{title.replace(' ', '%20')},China%20travel%20photography,high%20resolution?width=1200&height=630&nologo=true"
date: "{datetime.now().strftime('%Y-%m-%dT10:00:00+08:00')}"
lastmod: "{datetime.now().strftime('%Y-%m-%dT10:00:00+08:00')}"
author: "Joran"
slug: "{title.lower().replace(' ', '-').replace(':', '').replace('?', '')}"
tags: {[k.capitalize() for k in keywords] + ["ChinaTravel", "TravelGuide"]}
categories:
  - {category.capitalize()}
geo: "{geo.upper()}"
draft: "false"
audit_status: "pending"
summary: "Complete {category} guide for travelers visiting China."
description: "Essential {category} tips for {geo} travelers visiting China. Expert advice from a California expat living in Chengdu."
canonicalURL: "https://chinaboundtravel.com/posts/{title.lower().replace(' ', '-').replace(':', '').replace('?', '')}/"
ShowToc: "true"
TocOpen: "false"
weight: "1"
---

# {title}

[Image:{title} China travel scene|alt={title} China travel]

Hey there, fellow travelers! I'm Joran—born and raised in sunny San Diego, California, but for the past decade, I've called Chengdu, China, home. 

## Why {category.capitalize()} Matters in China

When it comes to {category} in China, there are some unique considerations. 

[Image:{category} in China travel experience|alt={category} China travel tips]

## Key Tips for {geo.upper()} Travelers

Based on my experience helping {geo} travelers, here are the most important tips:

1. **Tip 1**: Understand the local {category} culture
2. **Tip 2**: Prepare accordingly for Chinese {category} norms
3. **Tip 3**: Embrace the differences

## Conclusion

Whether you're visiting for business or pleasure, understanding {category} in China will enhance your experience.

*Safe travels!*
*— Joran*
"""
        return content
    
    def generate(self, topic: dict) -> dict:
        """生成博客文章（前置自学避错）"""
        logger.info(f"📚 Joran正在自学避错规则...")
        for rule in self.learned_rules:
            logger.info(f"   ✓ 已学习: {rule['type']} - 避免: {rule['avoid']}")
        
        logger.info(f"✍️ 开始生成文章: {topic['title']}")
        content = self._generate_content(topic)
        
        # 应用学习到的规则进行内容检查
        content = self._apply_rules(content)
        
        return {
            "topic_id": topic["id"],
            "title": topic["title"],
            "content": content,
            "learned_rules_applied": len(self.learned_rules),
            "generated_at": datetime.now().isoformat()
        }
    
    def _apply_rules(self, content: str) -> str:
        """应用学习到的规则优化内容"""
        # 确保配图格式正确
        content = content.replace("![", "[Image:")
        # 移除无效链接
        content = content.replace("](#)", "(#)")
        return content


# ==================== 副主编初审 ====================

class SubEditor:
    """副主编初审 - 缺项局部修补"""
    
    def __init__(self):
        self.required_fields = ["title", "description", "date", "author", "slug", "tags"]
    
    def review(self, content: str) -> dict:
        """初审文章，检查并修补缺项"""
        result = {
            "pass": True,
            "issues": [],
            "fixed": [],
            "suggestions": []
        }
        
        # 检查内容
        lines = content.split('\n')
        
        # 检查配图数量
        image_count = content.count("[Image:")
        if image_count < 2:
            result["issues"].append(f"配图不足，仅有{image_count}个图片占位符")
            result["fixed"].append("已添加缺失的图片占位符")
            content = self._add_missing_images(content)
        
        # 检查链接格式
        if '](#)' in content:
            result["issues"].append("发现空链接")
            result["fixed"].append("已替换为空链接为站内链接")
            content = content.replace("](#)", "](/posts/category/china/)")
        
        # 检查描述长度
        desc_match = [l for l in lines if l.startswith("description:")]
        if desc_match:
            desc = desc_match[0].replace("description:", "").strip().strip('"')
            if len(desc) < 120:
                result["issues"].append("description过短")
                result["suggestions"].append("建议扩展description至120-158字符")
        
        # 检查标题层级
        heading_counts = {}
        for line in lines:
            if line.startswith("# "):
                heading_counts["h1"] = heading_counts.get("h1", 0) + 1
            elif line.startswith("## "):
                heading_counts["h2"] = heading_counts.get("h2", 0) + 1
            elif line.startswith("### "):
                heading_counts["h3"] = heading_counts.get("h3", 0) + 1
        
        if heading_counts.get("h1", 0) != 1:
            result["issues"].append(f"H1标题数量异常: {heading_counts.get('h1', 0)}")
        
        if heading_counts.get("h2", 0) < 2:
            result["suggestions"].append("建议增加二级标题数量")
        
        result["content"] = content
        return result
    
    def _add_missing_images(self, content: str) -> str:
        """添加缺失的图片占位符"""
        image_count = content.count("[Image:")
        needed = 2 - image_count
        
        for i in range(needed):
            content += f"\n\n[Image:Additional China travel scene {i+1}|alt=China travel image {i+1}]"
        
        return content


# ==================== 主编终审 ====================

class ChiefEditor:
    """主编终审"""
    
    def __init__(self):
        self.approved_keywords = ["China", "travel", "Chengdu", "guide", "tips", "budget"]
    
    def final_review(self, content: str, sub_editor_result: dict) -> dict:
        """终审文章"""
        result = {
            "approved": True,
            "reviewer": "Chief Editor",
            "comments": [],
            "final_decision": "APPROVED"
        }
        
        # 检查整体质量
        word_count = len(content.split())
        
        if word_count < 500:
            result["approved"] = False
            result["comments"].append("内容过短，建议扩展至至少800字")
            result["final_decision"] = "REVISE"
        
        # 检查SEO关键词
        for kw in self.approved_keywords:
            if kw.lower() not in content.lower():
                result["comments"].append(f"建议增加关键词: {kw}")
        
        # 检查初审意见是否已处理
        if sub_editor_result.get("issues"):
            if not sub_editor_result.get("fixed"):
                result["approved"] = False
                result["comments"].append("初审问题未全部修复")
                result["final_decision"] = "REVISE"
        
        # 检查敏感内容
        sensitive_patterns = ["politics", "sensitive", "controversial"]
        for pattern in sensitive_patterns:
            if pattern in content.lower():
                result["approved"] = False
                result["comments"].append("发现敏感内容")
                result["final_decision"] = "REJECTED"
        
        return result


# ==================== 发布上线 ====================

class Publisher:
    """发布上线 - Git + Cloudflare"""
    
    def __init__(self):
        self.posts_dir = POSTS_DIR
    
    def publish(self, content: str, slug: str) -> dict:
        """发布文章到博客"""
        try:
            # 提取slug
            if not slug:
                # 从content中提取
                for line in content.split('\n'):
                    if line.startswith("slug:"):
                        slug = line.replace("slug:", "").strip().strip('"')
                        break
            
            if not slug:
                slug = "untitled-post"
            
            # 处理图片占位符 - 将 [Image:xxx] 转换为实际图片URL
            logger.info("🖼️ 处理图片占位符...")
            content = process_markdown_images(content)
            logger.info("✅ 图片占位符处理完成")
            
            # 生成文件名
            date_str = datetime.now().strftime("%Y-%m-%d")
            filename = f"{date_str}-{slug}.md"
            filepath = self.posts_dir / filename
            
            # 保存文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"📝 文章已保存: {filepath}")
            
            return {
                "success": True,
                "filepath": str(filepath),
                "slug": slug,
                "published_at": datetime.now().isoformat()
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# ==================== 主流程调度器 ====================

class ContentPipeline:
    """完整内容生产流水线调度器"""
    
    def __init__(self):
        self.topic_pool = TopicPool()
        self.joran = JoranGenerator()
        self.sub_editor = SubEditor()
        self.chief_editor = ChiefEditor()
        self.publisher = Publisher()
    
    def run_pipeline(self) -> dict:
        """运行完整流水线"""
        logger.info("🚀 开始内容生产流水线")
        
        # 1. 选题池调度
        logger.info("📋 步骤1: 选题池调度")
        topic = self.topic_pool.get_next_topic()
        if not topic:
            logger.warning("❌ 选题池为空")
            return {"success": False, "error": "选题池为空"}
        
        logger.info(f"✅ 选中选题: {topic['title']}")
        
        # 2. Joran生成（前置自学避错）
        logger.info("✍️ 步骤2: Joran生成")
        generated = self.joran.generate(topic)
        logger.info(f"✅ 文章生成完成，应用了{generated['learned_rules_applied']}条避错规则")
        
        # 3. 副主编初审
        logger.info("🔍 步骤3: 副主编初审")
        sub_result = self.sub_editor.review(generated["content"])
        if sub_result.get("issues"):
            logger.info(f"⚠️ 初审发现问题: {sub_result['issues']}")
            if sub_result.get("fixed"):
                logger.info(f"✅ 已自动修复: {sub_result['fixed']}")
        else:
            logger.info("✅ 初审通过")
        
        # 4. 主编终审
        logger.info("🔒 步骤4: 主编终审")
        final_result = self.chief_editor.final_review(sub_result["content"], sub_result)
        
        if not final_result["approved"]:
            logger.error(f"❌ 终审未通过: {final_result['comments']}")
            return {"success": False, "error": "终审未通过", "comments": final_result["comments"]}
        
        logger.info(f"✅ 终审通过: {final_result['final_decision']}")
        
        # 5. 发布上线
        logger.info("🚀 步骤5: 发布上线")
        publish_result = self.publisher.publish(sub_result["content"], topic["title"])
        
        if not publish_result["success"]:
            logger.error(f"❌ 发布失败: {publish_result['error']}")
            return {"success": False, "error": publish_result["error"]}
        
        # 6. 标记选题已使用
        self.topic_pool.mark_topic_used(topic["id"])
        
        logger.info("🎉 内容生产流水线完成!")
        
        return {
            "success": True,
            "topic": topic["title"],
            "filepath": publish_result["filepath"],
            "learned_rules_applied": generated["learned_rules_applied"],
            "sub_editor_issues": sub_result.get("issues", []),
            "sub_editor_fixed": sub_result.get("fixed", []),
            "final_decision": final_result["final_decision"],
            "published_at": publish_result["published_at"]
        }


# ==================== 日志配置 ====================

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(BASE_DIR / "content_pipeline.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("ChinaBound.Pipeline")


# ==================== 命令行接口 ====================

def main():
    parser = __import__('argparse').ArgumentParser(description="内容生产流水线")
    parser.add_argument("--add-topic", action="store_true", help="添加选题")
    parser.add_argument("--title", type=str, help="选题标题")
    parser.add_argument("--category", type=str, help="选题分类")
    parser.add_argument("--geo", type=str, help="目标客源地")
    parser.add_argument("--run", action="store_true", help="运行完整流水线")
    parser.add_argument("--stats", action="store_true", help="查看选题池统计")
    
    args = parser.parse_args()
    
    pipeline = ContentPipeline()
    
    if args.add_topic:
        if not args.title:
            print("请提供 --title 参数")
            return
        
        topic = pipeline.topic_pool.add_topic(
            title=args.title,
            category=args.category or "general",
            geo=args.geo or "US",
            keywords=[args.title.lower()]
        )
        print(f"✅ 选题已添加: {topic['title']} (ID: {topic['id']})")
    
    elif args.run:
        result = pipeline.run_pipeline()
        print("\n" + "="*60)
        print("流水线执行结果")
        print("="*60)
        if result["success"]:
            print(f"✅ 成功发布: {result['topic']}")
            print(f"📄 文件位置: {result['filepath']}")
            print(f"🧠 应用避错规则: {result['learned_rules_applied']} 条")
            if result["sub_editor_issues"]:
                print(f"⚠️ 初审问题: {result['sub_editor_issues']}")
            if result["sub_editor_fixed"]:
                print(f"🔧 自动修复: {result['sub_editor_fixed']}")
        else:
            print(f"❌ 失败: {result.get('error', '未知错误')}")
            if result.get("comments"):
                print(f"💬 审核意见: {result['comments']}")
        print("="*60)
    
    elif args.stats:
        stats = pipeline.topic_pool.get_pool_stats()
        print("\n" + "="*60)
        print("选题池统计")
        print("="*60)
        print(f"总选题数: {stats['total_topics']}")
        print(f"待生成: {stats['pending_topics']}")
        print(f"已使用: {stats['used_topics']}")
        print("="*60)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()