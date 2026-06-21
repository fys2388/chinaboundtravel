#!/usr/bin/env python3
"""
ChinaBoundTravel 关键词研究自动化脚本
功能：
1. 生成关键词变体
2. 自动分类搜索意图
3. 评估关键词优先级
4. 输出CSV格式的关键词研究表

使用方法：
    python keyword_research.py --seed "China travel guide" --output keywords.csv
    
或者使用内置种子词列表：
    python keyword_research.py --auto --output keywords.csv
"""

import csv
import re
import argparse
from datetime import datetime

# 内置种子关键词列表
SEED_KEYWORDS = {
    "一级-核心主题": [
        "China travel",
        "China visa",
        "visit China",
        "China guide",
        "travel to China",
    ],
    "二级-城市": [
        "Beijing travel",
        "Shanghai travel",
        "Chengdu travel",
        "Xian travel",
        "Guilin travel",
        "Chongqing travel",
    ],
    "三级-实用主题": [
        "China food",
        "China train",
        "China VPN",
        "China budget",
        "China itinerary",
        "China safety",
        "China packing",
        "China apps",
    ],
    "四级-长尾": [
        "144 hour visa free China",
        "China visa for US citizens",
        "best VPN for China",
        "how to use Didi in China",
        "China high speed train booking",
        "Chengdu food guide",
        "Beijing things to do",
        "Shanghai 3 day itinerary",
    ]
}

# 关键词变体模板
KEYWORD_PATTERNS = {
    "信息型": [
        "{seed} guide",
        "{seed} tips",
        "how to {seed}",
        "what is {seed}",
        "{seed} for beginners",
        "{seed} explained",
        "{seed} requirements",
        "{seed} process",
        "{seed} rules",
        "{seed} 2026",
    ],
    "交易型": [
        "best {seed}",
        "{seed} booking",
        "{seed} price",
        "cheap {seed}",
        "{seed} deals",
        "{seed} discount",
        "{seed} online",
        "{seed} reservation",
    ],
    "商业调研型": [
        "{seed} vs",
        "{seed} comparison",
        "{seed} review",
        "top {seed}",
        "{seed} alternatives",
        "best {seed} for",
        "{seed} recommendations",
    ],
    "问题型": [
        "is {seed} safe",
        "do I need {seed}",
        "can I {seed}",
        "what to {seed}",
        "when to {seed}",
        "where to {seed}",
        "how much {seed}",
    ]
}

# 高商业价值关键词标记
HIGH_VALUE_KEYWORDS = [
    "VPN", "insurance", "hotel", "flight", "booking", "ticket", "tour", "guide",
    "eSIM", "SIM", "money", "budget", "cost", "price", "deal", "discount"
]

# 中等商业价值关键词标记
MEDIUM_VALUE_KEYWORDS = [
    "visa", "itinerary", "transport", "metro", "train", "app", "pack", "safety",
    "food", "restaurant", "eat", "shopping", "souvenir"
]


def generate_keyword_variations(seed: str) -> list:
    """基于种子词生成关键词变体"""
    variations = []
    
    for intent_type, patterns in KEYWORD_PATTERNS.items():
        for pattern in patterns:
            keyword = pattern.format(seed=seed.lower())
            variations.append({
                "keyword": keyword,
                "seed": seed,
                "intent_type": intent_type,
            })
    
    return variations


def classify_search_intent(keyword: str) -> str:
    """自动分类搜索意图"""
    keyword_lower = keyword.lower()
    
    # 信息型特征词
    informational = ["how to", "what is", "guide", "tips", "explained", 
                     "requirements", "process", "rules", "for beginners",
                     "information", "about", "vs", "difference between"]
    
    # 交易型特征词
    transactional = ["buy", "book", "price", "cheap", "deal", "discount",
                     "booking", "reservation", "purchase", "order", "online"]
    
    # 商业调研型特征词
    commercial = ["best", "top", "review", "comparison", "compare",
                  "alternatives", "vs", "recommendations", "recommended"]
    
    # 问题型特征词
    question = ["is ", "do i", "can i", "what to", "when to", "where to",
                "how much", "why ", "should i"]
    
    # 判断逻辑（按优先级）
    if any(q in keyword_lower for q in question):
        return "问题型"
    elif any(t in keyword_lower for t in transactional):
        return "交易型"
    elif any(c in keyword_lower for c in commercial):
        return "商业调研型"
    elif any(i in keyword_lower for i in informational):
        return "信息型"
    else:
        return "信息型"  # 默认


def assess_commercial_value(keyword: str) -> str:
    """评估商业价值"""
    keyword_lower = keyword.lower()
    
    if any(hv in keyword_lower for hv in HIGH_VALUE_KEYWORDS):
        return "高"
    elif any(mv in keyword_lower for mv in MEDIUM_VALUE_KEYWORDS):
        return "中"
    else:
        return "低"


def assess_content_match(keyword: str) -> str:
    """评估与ChinaBoundTravel的内容匹配度"""
    keyword_lower = keyword.lower()
    
    # 高匹配度关键词
    high_match = ["china", "beijing", "shanghai", "chengdu", "xian", "guilin",
                  "chongqing", "visa", "travel", "trip", "visit", "guide",
                  "food", "train", "VPN", "itinerary", "budget", "safety",
                  "packing", "apps", "metro", "Didi"]
    
    # 中匹配度关键词
    medium_match = ["asia", "asian", "east asia", "backpacking", "solo travel",
                    "digital nomad", "expat", "living abroad"]
    
    if any(hm in keyword_lower for hm in high_match):
        return "高"
    elif any(mm in keyword_lower for mm in medium_match):
        return "中"
    else:
        return "低"


def calculate_priority(search_volume: int, seo_difficulty: int, 
                       commercial_value: str, content_match: str) -> int:
    """
    计算关键词优先级得分
    需要手动填入搜索量和SEO难度后计算
    """
    # 搜索量评分
    if search_volume >= 1000:
        volume_score = 5
    elif search_volume >= 500:
        volume_score = 4
    elif search_volume >= 100:
        volume_score = 3
    else:
        volume_score = 1
    
    # SEO难度评分（越低越好）
    if seo_difficulty <= 30:
        difficulty_score = 5
    elif seo_difficulty <= 50:
        difficulty_score = 4
    elif seo_difficulty <= 70:
        difficulty_score = 3
    else:
        difficulty_score = 1
    
    # 商业价值评分
    value_scores = {"高": 5, "中": 3, "低": 1}
    value_score = value_scores.get(commercial_value, 1)
    
    # 内容匹配度评分
    match_scores = {"高": 5, "中": 3, "低": 1}
    match_score = match_scores.get(content_match, 1)
    
    # 加权计算
    total_score = (
        volume_score * 0.30 +
        difficulty_score * 0.25 +
        value_score * 0.25 +
        match_score * 0.20
    )
    
    return round(total_score * 10)  # 转换为0-50的整数


def generate_content_suggestion(keyword: str, intent_type: str) -> str:
    """基于关键词生成内容建议"""
    if intent_type == "信息型":
        return f"指南/教程型文章：'{keyword.title()} - Complete Guide (2026)'"
    elif intent_type == "交易型":
        return f"产品推荐/对比文章：'Best {keyword.title()} - Top Recommendations'"
    elif intent_type == "商业调研型":
        return f"对比评测文章：'{keyword.title()} - Detailed Comparison'"
    elif intent_type == "问题型":
        return f"FAQ/解答文章：'{keyword.title()}? - Everything You Need to Know'"
    else:
        return f"综合指南：'{keyword.title()} - Ultimate Guide'"


def generate_keywords_from_seeds() -> list:
    """从内置种子词列表生成所有关键词变体"""
    all_keywords = []
    
    for category, seeds in SEED_KEYWORDS.items():
        for seed in seeds:
            variations = generate_keyword_variations(seed)
            all_keywords.extend(variations)
    
    return all_keywords


def export_to_csv(keywords: list, output_file: str):
    """导出关键词到CSV文件"""
    fieldnames = [
        "序号", "关键词", "种子词", "搜索意图", "商业价值",
        "内容匹配度", "搜索量(月)", "SEO难度", "优先级得分",
        "内容建议", "状态"
    ]
    
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for idx, kw in enumerate(keywords, 1):
            # 自动评估
            intent = classify_search_intent(kw["keyword"])
            commercial = assess_commercial_value(kw["keyword"])
            match = assess_content_match(kw["keyword"])
            content_suggestion = generate_content_suggestion(kw["keyword"], intent)
            
            # 计算优先级（使用默认搜索量0，需要手动更新）
            priority = calculate_priority(0, 0, commercial, match)
            
            writer.writerow({
                "序号": idx,
                "关键词": kw["keyword"],
                "种子词": kw["seed"],
                "搜索意图": intent,
                "商业价值": commercial,
                "内容匹配度": match,
                "搜索量(月)": "",  # 需要手动填入
                "SEO难度": "",   # 需要手动填入
                "优先级得分": priority,
                "内容建议": content_suggestion,
                "状态": "待研究"
            })
    
    print(f"✅ 已生成 {len(keywords)} 个关键词到 {output_file}")
    print("📋 下一步：使用Ubersuggest/Google Keyword Planner查询搜索量和SEO难度")
    print("   填入CSV后，优先级得分会自动更新")


def update_priorities(input_file: str, output_file: str):
    """基于填入的搜索量和SEO难度更新优先级"""
    keywords = []
    
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 获取填入的数据
            try:
                volume = int(row["搜索量(月)"]) if row["搜索量(月)"] else 0
            except:
                volume = 0
            
            try:
                difficulty = int(row["SEO难度"]) if row["SEO难度"] else 0
            except:
                difficulty = 0
            
            # 重新计算优先级
            if volume > 0 and difficulty > 0:
                priority = calculate_priority(
                    volume, difficulty, 
                    row["商业价值"], row["内容匹配度"]
                )
                row["优先级得分"] = priority
                row["状态"] = "已研究"
            
            keywords.append(row)
    
    # 按优先级排序
    keywords.sort(key=lambda x: int(x["优先级得分"]), reverse=True)
    
    # 重新编号
    for idx, kw in enumerate(keywords, 1):
        kw["序号"] = idx
    
    # 导出
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=keywords[0].keys())
        writer.writeheader()
        writer.writerows(keywords)
    
    print(f"✅ 已更新优先级并排序，导出到 {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="ChinaBoundTravel 关键词研究自动化脚本"
    )
    parser.add_argument(
        "--seed", 
        type=str, 
        help="单个种子关键词（如 'China travel guide'）"
    )
    parser.add_argument(
        "--auto", 
        action="store_true", 
        help="使用内置种子词列表自动生成"
    )
    parser.add_argument(
        "--output", 
        type=str, 
        default="keywords.csv",
        help="输出CSV文件名（默认: keywords.csv）"
    )
    parser.add_argument(
        "--update",
        type=str,
        help="更新已填入数据的CSV文件（输入文件名）"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("   ChinaBoundTravel 关键词研究自动化脚本")
    print("=" * 60)
    print()
    
    if args.update:
        # 更新模式
        update_priorities(args.update, args.output)
    elif args.auto:
        # 自动模式：使用内置种子词
        print("🚀 使用内置种子词列表生成关键词...")
        keywords = generate_keywords_from_seeds()
        export_to_csv(keywords, args.output)
    elif args.seed:
        # 单种子模式
        print(f"🚀 基于种子词 '{args.seed}' 生成关键词...")
        keywords = generate_keyword_variations(args.seed)
        export_to_csv(keywords, args.output)
    else:
        # 默认模式：使用内置种子词
        print("🚀 使用内置种子词列表生成关键词...")
        print("   提示：使用 --seed 指定单个种子词，或 --auto 使用完整列表")
        print()
        keywords = generate_keywords_from_seeds()
        export_to_csv(keywords, args.output)
    
    print()
    print("=" * 60)
    print("📊 使用建议：")
    print("   1. 打开生成的CSV文件")
    print("   2. 使用Ubersuggest/Google Keyword Planner查询搜索量")
    print("   3. 填入'搜索量(月)'和'SEO难度'列")
    print("   4. 运行：python keyword_research.py --update keywords.csv")
    print("   5. 查看按优先级排序的结果")
    print("=" * 60)


if __name__ == "__main__":
    main()
