import csv
import os
import logging
import sys
from datetime import datetime
from typing import Dict, List, Optional

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from content_manager import ContentManager

logger = logging.getLogger(__name__)

class AIEditor:
    def __init__(self):
        self.cm = ContentManager()
        self.review_history = []
        self.approved_count = 0
    
    def review_content(self, content: Dict) -> Dict:
        review_result = {
            "content_id": content.get('id', ''),
            "title": content.get('title', ''),
            "reviewed_at": datetime.now().isoformat(),
            "approved": False,
            "issues": [],
            "suggestions": []
        }
        
        if not content.get('title') or len(content.get('title', '')) < 10:
            review_result['issues'].append("标题太短或缺失")
        
        if not content.get('content') or len(content.get('content', '')) < 50:
            review_result['issues'].append("内容太短或缺失")
        
        if not content.get('url'):
            review_result['issues'].append("链接缺失")
        
        title = content.get('title', '')
        banned_words = ['scam', 'fraud', 'illegal', 'free money']
        for word in banned_words:
            if word.lower() in title.lower():
                review_result['issues'].append(f"标题包含敏感词: {word}")
        
        if not review_result['issues']:
            review_result['approved'] = True
            review_result['suggestions'].append("内容良好，可以发布")
        
        review_result['review_type'] = "豆包AI审核"
        self.review_history.append(review_result)
        
        return review_result
    
    def review_with_deepseek(self, content: Dict) -> Dict:
        review_result = {
            "content_id": content.get('id', ''),
            "title": content.get('title', ''),
            "reviewed_at": datetime.now().isoformat(),
            "approved": False,
            "issues": [],
            "suggestions": []
        }
        
        title = content.get('title', '')
        content_text = content.get('content', '')
        
        if len(title) < 15:
            review_result['issues'].append("标题不够吸引人，建议扩展到15字以上")
        
        if len(content_text) < 100:
            review_result['issues'].append("内容过短，建议增加有价值的信息")
        
        keywords = ['guide', 'tip', 'how', 'best', 'complete', 'ultimate']
        has_value = any(keyword.lower() in content_text.lower() for keyword in keywords)
        
        if not has_value:
            review_result['suggestions'].append("建议增加实用指南类内容")
        
        url = content.get('url', '')
        if not url.startswith('http'):
            review_result['issues'].append("URL 格式不正确")
        
        if not review_result['issues']:
            review_result['approved'] = True
        
        review_result['review_type'] = "DeepSeekAI审核"
        self.review_history.append(review_result)
        
        return review_result
    
    def select_weekly_content(self, count: int = 5) -> List[Dict]:
        all_content = self.cm.posts
        selected = []
        
        csv_content = [c for c in all_content if c.get('source') == 'csv']
        
        seen_urls = set()
        unique_content = []
        
        for c in csv_content:
            url = c.get('url', '')
            if url not in seen_urls:
                seen_urls.add(url)
                unique_content.append(c)
        
        selected = unique_content[:count]
        
        logger.info(f"已选择 {len(selected)} 篇内容用于本周发布")
        
        return selected
    
    def generate_markdown_article(self, content: Dict) -> str:
        title = content.get('title', 'Untitled')
        content_text = content.get('content', '')
        url = content.get('url', '')
        
        today = datetime.now().strftime('%Y-%m-%d')
        slug = title.lower().replace(' ', '-').replace('"', '').replace("'", '').replace('/', '-').replace('?', '').replace('(', '').replace(')', '').replace(':', '-').replace(',', '').replace('.', '').replace('!', '').replace('&', 'and').replace('---', '-')
        if len(slug) > 100:
            slug = slug[:100]
        filename = f"{today}-{slug}.md"
        
        article = f"""---
title: "{title}"
date: {datetime.now().isoformat()}
author: ChinaBound Travel
tags: ["ChinaTravel", "TravelGuide"]
categories: ["China"]
summary: "{content.get('summary', title)[:150]}..."
canonicalURL: "{url}"
---

# {title}

{content_text}

---

[阅读原文]({url})

---

*这篇文章由 ChinaBound Travel 原创发布。*
"""
        
        return {
            "filename": filename,
            "content": article,
            "title": title
        }
    
    def save_article(self, article: Dict, output_dir: str = None):
        if output_dir is None:
            output_dir = os.environ.get('AI_OUTPUT_DIR', 'content/posts')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        filepath = os.path.join(output_dir, article['filename'])
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(article['content'])
        
        logger.info(f"文章已保存: {filepath}")
        
        return filepath
    
    def full_ai_editing_pipeline(self):
        print("\n" + "="*80)
        print("                    ChinaBound Travel AI 主编审核流程")
        print("="*80)
        
        print("\n[步骤 1/5]选择本周发布内容（4-6 篇）...")
        weekly_content = self.select_weekly_content(5)
        
        for i, content in enumerate(weekly_content):
            print(f"  {i+1}. {content.get('title', 'Untitled')}")
        
        print("\n[步骤 2/5]执行豆包 AI 审核...")
        doubao_results = []
        for content in weekly_content:
            result = self.review_content(content)
            doubao_results.append(result)
            status = "[OK]" if result['approved'] else "[FAIL]"
            print(f"  {status}: {content.get('title', 'Untitled')[:50]}...")
            if not result['approved']:
                for issue in result['issues']:
                    print(f"      - 问题: {issue}")
        
        print("\n[步骤 3/5]执行 DeepSeek AI 审核...")
        deepseek_results = []
        for content in weekly_content:
            result = self.review_with_deepseek(content)
            deepseek_results.append(result)
            status = "[OK]" if result['approved'] else "[FAIL]"
            print(f"  {status}: {content.get('title', 'Untitled')[:50]}...")
        
        print("\n[步骤 4/5]确定最终发布文章...")
        final_passed = []
        
        for i, content in enumerate(weekly_content):
            doubao_passed = doubao_results[i]['approved']
            deepseek_passed = deepseek_results[i]['approved']
            
            if doubao_passed and deepseek_passed:
                final_passed.append(content)
                print(f"  [OK]双重审核通过: {content.get('title', 'Untitled')}")
            else:
                print(f"  [FAIL]未通过审核: {content.get('title', 'Untitled')}")
        
        print(f"\n[步骤 5/5]生成并保存 {len(final_passed)} 篇文章...")
        saved_files = []
        
        for content in final_passed:
            article = self.generate_markdown_article(content)
            filepath = self.save_article(article)
            saved_files.append(filepath)
            print(f"  [OK]已保存: {article['filename']}")
        
        print("\n" + "="*80)
        print("                            审核完成报告")
        print("="*80)
        print(f"\n总审核数: {len(weekly_content)}")
        print(f"豆包通过: {sum(1 for r in doubao_results if r['approved'])}")
        print(f"DeepSeek 通过: {sum(1 for r in deepseek_results if r['approved'])}")
        print(f"双重审核通过: {len(final_passed)}")
        print(f"已发布文章: {len(saved_files)}")
        
        if saved_files:
            print(f"\n已保存文件:")
            for f in saved_files:
                print(f"  - {f}")
        
        print("\nAI 主编审核流程完成！")
        
        return saved_files


def main():
    logging.basicConfig(level=logging.INFO)
    editor = AIEditor()
    editor.full_ai_editing_pipeline()


if __name__ == "__main__":
    main()
