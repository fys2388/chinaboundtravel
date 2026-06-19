import os
import glob
from datetime import datetime

def main():
    posts_dir = "content/posts"
    files = glob.glob(f"{posts_dir}/*.md")
    
    # 关键词映射表
    keyword_map = {
        "wechat": ["WeChat Pay", "mobile payment", "China payment", "foreigners", "WeChat wallet", "digital payment"],
        "alipay": ["Alipay", "mobile payment", "China payment", "foreigners", "digital payment", "Chinese bank card"],
        "visa": ["visa-free", "China visa", "transit visa", "144-hour visa", "China travel"],
        "train": ["high-speed rail", "train tickets", "China trains", "HSR", "transportation"],
        "panda": ["Chengdu pandas", "Panda Base", "Sichuan", "panda tour"],
        "food": ["Chinese food", "hot pot", "Sichuan cuisine", "street food", "delivery"],
        "internet": ["VPN", "eSIM", "China internet", "Great Firewall"],
        "shanghai": ["Shanghai", "Bund", "French Concession", "city guide"],
        "beijing": ["Beijing", "Forbidden City", "Great Wall", "city guide"],
        "chengdu": ["Chengdu", "pandas", "hot pot", "Sichuan", "city guide"],
        "xian": ["Xi'an", "Terracotta Warriors", "Muslim Quarter", "city guide"],
        "guide": ["travel guide", "China travel tips", "China travel guide"],
    }
    
    # FAQ 模板
    faq_templates = {
        "payment": [
            {
                "question": "Can foreigners use WeChat Pay in China?",
                "answer": "Yes, foreigners can use WeChat Pay with a foreign credit card (Visa, Mastercard, etc.) or by opening a Chinese bank account."
            },
            {
                "question": "Is Alipay available for non-Chinese users?",
                "answer": "Absolutely! Alipay supports foreign credit cards and passport verification for international travelers."
            },
            {
                "question": "What's the best way to pay in China as a foreigner?",
                "answer": "Set up Alipay or WeChat Pay before your trip. Carry some cash as backup, and get a Chinese bank account if you're staying long-term."
            }
        ],
        "general": [
            {
                "question": "Is China safe for foreign tourists?",
                "answer": "Yes, China is very safe for tourists. Violent crime is rare, and cities are generally safe day and night."
            },
            {
                "question": "What's the best time to visit China?",
                "answer": "Spring (April-May) and autumn (September-October) offer the best weather, with mild temperatures and fewer crowds."
            },
            {
                "question": "Do I need a VPN for China?",
                "answer": "Yes, most Western apps and websites are blocked. An eSIM with VPN service is recommended for reliable internet access."
            }
        ],
        "cities": [
            {
                "question": "What cities should I visit in China?",
                "answer": "Beijing, Shanghai, Chengdu, and Xi'an are great starting points. Each offers unique experiences from history to food to pandas."
            },
            {
                "question": "How do I get around Chinese cities?",
                "answer": "Subway systems in major cities are excellent. Taxis and ride-hailing apps (Didi) are cheap and convenient."
            }
        ]
    }
    
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 分离 front matter 和正文
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    frontmatter = parts[1]
                    body = parts[2]
                    
                    # 检查是否已有完整字段
                    needs_update = False
                    new_frontmatter = frontmatter
                    
                    # 检查并补充缺失字段
                    if 'description:' not in frontmatter:
                        # 从 summary 提取或从标题生成
                        title = ""
                        summary = ""
                        for line in frontmatter.split('\n'):
                            if line.strip().startswith('title:'):
                                title = line.split(':', 1)[1].strip().strip('"')
                            if line.strip().startswith('summary:'):
                                summary = line.split(':', 1)[1].strip().strip('"')
                        
                        description = summary if summary else f"Practical guide to {title} by Joran, an American living in China."
                        new_frontmatter += f'\ndescription: "{description}"'
                        needs_update = True
                    
                    if 'author:' not in frontmatter:
                        new_frontmatter += '\nauthor: "Joran"'
                        needs_update = True
                    
                    if 'params:' not in frontmatter and 'keywords:' not in frontmatter:
                        # 生成关键词
                        title_lower = title.lower()
                        keywords = []
                        for key, kw_list in keyword_map.items():
                            if key in title_lower:
                                keywords.extend(kw_list)
                        if not keywords:
                            keywords = keyword_map["general"][:3]
                        
                        # 生成 FAQ
                        faq_list = []
                        if any(k in title_lower for k in ["alipay", "wechat", "payment"]):
                            faq_list = faq_templates.get("payment", [])
                        elif any(k in title_lower for k in ["shanghai", "beijing", "chengdu", "xian"]):
                            faq_list = faq_templates.get("cities", [])
                        else:
                            faq_list = faq_templates.get("general", [])
                        
                        # 添加 params
                        new_frontmatter += '\nparams:'
                        new_frontmatter += '\n  keywords:'
                        for kw in keywords[:6]:
                            new_frontmatter += f'\n    - "{kw}"'
                        new_frontmatter += '\n  faq:'
                        for faq in faq_list[:5]:
                            new_frontmatter += '\n    - question: "' + faq['question'] + '"'
                            new_frontmatter += '\n      answer: "' + faq['answer'] + '"'
                        
                        needs_update = True
                    
                    if needs_update:
                        # 重新组合内容
                        new_content = f'---\n{new_frontmatter.strip()}\n---\n{body}'
                        
                        # 写回文件
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        
                        print(f"Updated: {os.path.basename(filepath)}")
        
        except Exception as e:
            print(f"Error processing {filepath}: {e}")

if __name__ == "__main__":
    main()
