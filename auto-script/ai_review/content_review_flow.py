#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 内容审核流程脚本 - 标签校验规则
实现「AI副主编 → AI主编」双审核机制
"""

import os
import sys
import json
import requests
from pathlib import Path

# 内容标签规则
TAG_RULES = {
    "posts": {"allowed": [], "forbidden": ["[Static-Package]", "[Monthly-Update]", "[Annual-Exclusive]"]},
    "static-package": {"allowed": ["[Static-Package]"], "forbidden": ["[Monthly-Update]", "[Annual-Exclusive]"]},
    "member-month": {"allowed": ["[Monthly-Update]", "[Static-Package]"], "forbidden": ["[Annual-Exclusive]"]},
    "member-year": {"allowed": ["[Annual-Exclusive]", "[Monthly-Update]", "[Static-Package]"], "forbidden": []}
}

# 飞书 Webhook URL
FEISHU_WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/***REMOVED***"

class ContentReviewFlow:
    def __init__(self):
        self.results = {
            "passed": [],
            "rejected": [],
            "rewritten": [],
            "archived": []
        }
    
    def extract_tags(self, content):
        """从内容中提取标签"""
        tags = []
        for tag in ["[Static-Package]", "[Monthly-Update]", "[Annual-Exclusive]"]:
            if tag in content:
                tags.append(tag)
        return tags
    
    def determine_category(self, filepath):
        """根据文件路径确定内容分类"""
        if "/posts/" in filepath:
            return "posts"
        elif "/static-package/" in filepath:
            return "static-package"
        elif "/member-month/" in filepath:
            return "member-month"
        elif "/member-year/" in filepath:
            return "member-year"
        return None
    
    def check_tag_rules(self, category, tags):
        """检查标签是否符合规则"""
        if category not in TAG_RULES:
            return False, f"未知分类: {category}"
        
        rules = TAG_RULES[category]
        errors = []
        
        # 检查是否有禁止的标签
        for tag in tags:
            if tag in rules["forbidden"]:
                errors.append(f"包含禁止标签: {tag}")
        
        # 检查是否缺少必需标签（付费内容）
        if category != "posts" and not tags:
            errors.append("缺少必需标签")
        
        if errors:
            return False, "; ".join(errors)
        return True, "标签校验通过"
    
    def ai_assistant_review(self, filepath):
        """AI 副主编审核"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            category = self.determine_category(filepath)
            tags = self.extract_tags(content)
            
            if category is None:
                return "reject", "无法确定内容分类"
            
            passed, message = self.check_tag_rules(category, tags)
            
            if passed:
                return "pass", f"标签校验通过 - 分类: {category}, 标签: {tags}"
            else:
                return "reject", message
                
        except Exception as e:
            return "reject", f"读取文件失败: {str(e)}"
    
    def ai_editor_review(self, filepath, first_review_result):
        """AI 主编审核 - 二次审核"""
        if first_review_result[0] == "pass":
            return "pass", "AI主编: 审核通过"
        
        # 尝试自动修复
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            category = self.determine_category(filepath)
            tags = self.extract_tags(content)
            
            # 自动移除禁止的标签
            rules = TAG_RULES.get(category, {})
            new_content = content
            removed_tags = []
            
            for forbidden_tag in rules.get("forbidden", []):
                if forbidden_tag in new_content:
                    new_content = new_content.replace(forbidden_tag, "")
                    removed_tags.append(forbidden_tag)
            
            # 如果移除了标签，尝试添加正确的标签
            if removed_tags and category != "posts":
                recommended_tag = {
                    "static-package": "[Static-Package]",
                    "member-month": "[Monthly-Update]",
                    "member-year": "[Annual-Exclusive]"
                }.get(category)
                if recommended_tag and recommended_tag not in new_content:
                    # 在文章末尾添加标签
                    new_content += f"\n\n{recommended_tag}"
            
            if removed_tags:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return "rewrite", f"AI主编: 自动修复完成，移除标签: {removed_tags}"
            
            return "reject", f"AI主编: 无法自动修复"
            
        except Exception as e:
            return "reject", f"AI主编审核失败: {str(e)}"
    
    def archive_post(self, filepath):
        """归档废稿"""
        archive_dir = Path(filepath).parent / ".archived"
        archive_dir.mkdir(exist_ok=True)
        
        filename = Path(filepath).name
        archive_path = archive_dir / filename
        
        os.rename(filepath, archive_path)
        return str(archive_path)
    
    def send_feishu_alert(self, filepath, status, message):
        """发送飞书告警"""
        alert_message = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": "⚠️ 内容审核告警"
                    },
                    "template": "red" if status == "archive" else "orange"
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**文件**: `{filepath}`\n**状态**: {status}\n**原因**: {message}"
                        }
                    },
                    {
                        "tag": "note",
                        "elements": [
                            {"tag": "plain_text", "content": "ChinaBound Travel AI 审核系统"}
                        ]
                    }
                ]
            }
        }
        
        try:
            requests.post(
                FEISHU_WEBHOOK_URL,
                headers={"Content-Type": "application/json"},
                data=json.dumps(alert_message),
                timeout=30
            )
        except Exception:
            pass
    
    def review_file(self, filepath):
        """审核单个文件"""
        print(f"\n审核文件: {filepath}")
        
        # 第一轮：AI 副主编审核
        first_result = self.ai_assistant_review(filepath)
        print(f"  AI副主编: {first_result[1]}")
        
        if first_result[0] == "pass":
            self.results["passed"].append({"file": filepath, "message": first_result[1]})
            print("  ✅ 审核通过")
            return "pass"
        
        # 第二轮：AI 主编审核（尝试自动修复）
        second_result = self.ai_editor_review(filepath, first_result)
        print(f"  AI主编: {second_result[1]}")
        
        if second_result[0] == "pass":
            self.results["passed"].append({"file": filepath, "message": second_result[1]})
            print("  ✅ 审核通过")
            return "pass"
        elif second_result[0] == "rewrite":
            self.results["rewritten"].append({"file": filepath, "message": second_result[1]})
            print("  ⚠️ 自动修复完成")
            return "rewrite"
        else:
            # 归档废稿
            archive_path = self.archive_post(filepath)
            self.results["archived"].append({"file": filepath, "message": f"已归档到 {archive_path}"})
            self.send_feishu_alert(filepath, "archive", second_result[1])
            print("  ❌ 已归档废稿并发送告警")
            return "archive"
    
    def run_batch_review(self, directory="content"):
        """批量审核目录下所有文件"""
        print("=" * 60)
        print("AI 内容审核流程启动")
        print("=" * 60)
        
        md_files = list(Path(directory).rglob("*.md"))
        
        for md_file in md_files:
            filepath = str(md_file)
            # 跳过归档目录和草稿目录
            if ".archived" in filepath or "/drafts/" in filepath:
                continue
            self.review_file(filepath)
        
        self.print_summary()
    
    def print_summary(self):
        """打印审核总结"""
        print("\n" + "=" * 60)
        print("审核总结")
        print("=" * 60)
        print(f"✅ 通过: {len(self.results['passed'])}")
        print(f"⚠️ 自动修复: {len(self.results['rewritten'])}")
        print(f"❌ 归档: {len(self.results['archived'])}")
        
        if self.results['archived']:
            print("\n归档文件列表:")
            for item in self.results['archived']:
                print(f"  - {item['file']}: {item['message']}")

def main():
    if len(sys.argv) > 1:
        # 审核单个文件
        filepath = sys.argv[1]
        reviewer = ContentReviewFlow()
        reviewer.review_file(filepath)
    else:
        # 批量审核
        reviewer = ContentReviewFlow()
        reviewer.run_batch_review()

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    main()
