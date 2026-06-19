import os
import glob

def main():
    posts_dir = "content/posts"
    files = glob.glob(f"{posts_dir}/*.md")
    
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
                    
                    # 检查是否有缺失字段
                    has_description = 'description:' in frontmatter
                    has_author = 'author:' in frontmatter
                    has_params = 'params:' in frontmatter
                    has_keywords = 'keywords:' in frontmatter
                    has_faq = 'faq:' in frontmatter
                    
                    if not (has_description and has_author and has_params and has_keywords and has_faq):
                        # 提取标题
                        title = ""
                        summary = ""
                        for line in frontmatter.split('\n'):
                            if line.strip().startswith('title:'):
                                title = line.split(':', 1)[1].strip().strip('"')
                            if line.strip().startswith('summary:'):
                                summary = line.split(':', 1)[1].strip().strip('"')
                        
                        # 构建新的 front matter
                        new_lines = []
                        for line in frontmatter.split('\n'):
                            line = line.rstrip()
                            if line:
                                new_lines.append(line)
                        
                        # 添加缺失字段
                        if not has_description:
                            description = summary if summary else f"Practical guide to {title} by Joran, an American living in China."
                            new_lines.append(f'description: "{description}"')
                        
                        if not has_author:
                            new_lines.append('author: "Joran"')
                        
                        if not has_params or not has_keywords or not has_faq:
                            if not has_params:
                                new_lines.append('params:')
                            
                            if not has_keywords:
                                # 基于标题生成关键词
                                keywords = []
                                title_lower = title.lower()
                                if any(k in title_lower for k in ["wechat", "alipay", "payment"]):
                                    keywords = ["WeChat Pay", "Alipay", "mobile payment", "China payment", "foreigners", "digital payment"]
                                elif any(k in title_lower for k in ["train", "rail", "12306"]):
                                    keywords = ["high-speed rail", "China trains", "train tickets", "transportation", "12306", "HSR"]
                                elif any(k in title_lower for k in ["visa"]):
                                    keywords = ["China visa", "visa-free", "transit visa", "144-hour visa", "China travel"]
                                elif any(k in title_lower for k in ["panda", "chengdu"]):
                                    keywords = ["Chengdu pandas", "Panda Base", "Sichuan", "panda tour", "hot pot"]
                                elif any(k in title_lower for k in ["shanghai", "beijing", "xian"]):
                                    keywords = ["city guide", "China travel", "tourism", "travel tips"]
                                elif any(k in title_lower for k in ["internet", "vpn", "esim"]):
                                    keywords = ["VPN", "eSIM", "China internet", "Great Firewall", "travel tech"]
                                else:
                                    keywords = ["China travel", "travel guide", "travel tips", "China tourism"]
                                
                                new_lines.append('  keywords:')
                                for kw in keywords[:6]:
                                    new_lines.append(f'    - "{kw}"')
                            
                            if not has_faq:
                                faq_list = []
                                title_lower = title.lower()
                                if any(k in title_lower for k in ["alipay", "wechat", "payment"]):
                                    faq_list = [
                                        {"question": "Can foreigners use WeChat Pay in China?", "answer": "Yes, foreigners can use WeChat Pay with a foreign credit card or by opening a Chinese bank account."},
                                        {"question": "Is Alipay available for non-Chinese users?", "answer": "Absolutely! Alipay supports foreign credit cards and passport verification for international travelers."},
                                        {"question": "What's the best way to pay in China as a foreigner?", "answer": "Set up Alipay or WeChat Pay before your trip. Carry some cash as backup."}
                                    ]
                                else:
                                    faq_list = [
                                        {"question": "Is China safe for foreign tourists?", "answer": "Yes, China is very safe for tourists. Violent crime is rare, and cities are generally safe day and night."},
                                        {"question": "What's the best time to visit China?", "answer": "Spring (April-May) and autumn (September-October) offer the best weather, with mild temperatures and fewer crowds."},
                                        {"question": "Do I need a VPN for China?", "answer": "Yes, most Western apps and websites are blocked. An eSIM with VPN service is recommended for reliable internet access."}
                                    ]
                                
                                new_lines.append('  faq:')
                                for faq in faq_list[:5]:
                                    new_lines.append(f'    - question: "{faq["question"]}"')
                                    new_lines.append(f'      answer: "{faq["answer"]}"')
                        
                        # 重新组合内容
                        new_frontmatter = '\n'.join(new_lines)
                        new_content = f'---\n{new_frontmatter}\n---\n{body}'
                        
                        # 写回文件
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        
                        print(f"Updated: {os.path.basename(filepath)}")
        
        except Exception as e:
            print(f"Error processing {filepath}: {e}")

if __name__ == "__main__":
    main()
