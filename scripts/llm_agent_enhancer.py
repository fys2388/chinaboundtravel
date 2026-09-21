#!/usr/bin/env python3
"""
LLM Agent Enhancer - 为各 Agent 提供 LLM 增强能力

统一入口，支持：
1. Commerce Agent - LLM 个性化联盟推荐
2. User Agent - LLM 用户意图分析
3. Conversion Agent - LLM CTA 变体生成
4. Revenue Agent - LLM 营收洞察

使用方式:
    from llm_agent_enhancer import LLMEnhancer
    
    enhancer = LLMEnhancer()
    
    # Commerce: 个性化联盟推荐
    result = enhancer.personalize_affiliate({
        "user_context": {"origin": "USA", "duration": "10 days"},
        "available_products": [...]
    })
    
    # User: 意图分析
    result = enhancer.analyze_user_intent({
        "behavior": ["read_visa_article", "clicked_esim_link"],
        "session_duration": 300
    })
    
    # Conversion: CTA 变体
    result = enhancer.generate_cta_variants({
        "article_type": "payment_guide",
        "audience": "first_time_visitors"
    })
    
    # Revenue: 营收洞察
    result = enhancer.analyze_revenue_trends({
        "revenue_data": {...},
        "traffic_data": {...}
    })
"""

from __future__ import annotations

import json
import logging
import sys
import io
from pathlib import Path
from typing import Any, Dict, List, Optional

# Windows 编码修复
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 导入 LLM 分析器
try:
    from llm_analyzer import LLMAnalyzer
    _LLM_AVAILABLE = True
except ImportError:
    _LLM_AVAILABLE = False

logger = logging.getLogger("llm_agent_enhancer")

# ============ Prompt 模板 ============

COMMERCE_PERSONALIZE_PROMPT = """You are a travel affiliate recommendation engine.

User: {origin}, {duration}, cities: {cities}, interests: {interests}

Products: {products}

Return JSON with max 3 recommendations:
{{"recommendations":[{{"name":"...","provider":"...","price":"...","url":"...","reason":"...","urgency":1-10}}],"summary":"...","roi":"low|medium|high"}}

JSON only, no markdown."""

USER_INTENT_PROMPT = """You are a user intent analyzer.

Behavior: {actions}, duration: {session_duration}s, pages: {pages_visited}, page: {current_page}, device: {device_type}, source: {traffic_source}

Return JSON:
{{"intent":"research|booking|information|abandonment","confidence":0.0-1.0,"next_action":"...","engagement":1-10,"conversion":"low|medium|high","risk":"low|medium|high"}}

JSON only."""

CONVERSION_CTA_PROMPT = """You are a conversion copywriter.

Article: {article_type} about {topic}, audience: {audience}, current CTA: {current_cta}

Return 3 CTA variants as JSON:
{{"variants":[{{"id":1,"text":"...","style":"urgency|social_proof|value|curiosity","lift":"5-15%","reason":"..."}}],"recommended":1,"test":"..."}}

JSON only."""

REVENUE_INSIGHT_PROMPT = """You are a revenue analytics engine.

Revenue: {period}, ${total_revenue}, {affiliate_clicks} clicks, {conversion_rate}% CR, ${aov} AOV, top: {top_categories}
Traffic: {total_visits} visits, {pages_per_visit} ppv, {bounce_rate}% bounce, {organic_traffic}% organic

Return JSON:
{{"trend":"up|down|stable","growth":"...","rpv":"...","opportunities":[{{"category":"...","opportunity":"...","impact":"$...","priority":"high|medium|low"}}],"risks":[{{"risk":"...","mitigation":"..."}}],"summary":"..."}}

JSON only."""


import re as _re

def _parse_json_response(content: str) -> Optional[dict]:
    """Robustly parse JSON from LLM response, handling markdown code blocks."""
    if not content:
        return None
    
    content = content.strip()
    
    # Try direct parse first
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON from markdown code blocks
    # Pattern 1: ```json ... ```
    match = _re.search(r'```json\s*(\{[\s\S]*?\})\s*```', content)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Pattern 2: ``` ... ``` (without json label)
    match = _re.search(r'```\s*(\{[\s\S]*?\})\s*```', content)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Pattern 3: Extract the first JSON object found
    match = _re.search(r'(\{[\s\S]*\})', content)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    
    return None


class LLMEnhancer:
    """LLM Agent 增强器 - 为各 Agent 提供 LLM 能力"""
    
    def __init__(self):
        self.llm = LLMAnalyzer() if _LLM_AVAILABLE else None
        self.available = self.llm is not None and self.llm.available
    
    def personalize_affiliate(
        self,
        user_context: dict,
        available_products: List[dict] = None
    ) -> Optional[dict]:
        """Commerce Agent: LLM 个性化联盟推荐
        
        Args:
            user_context: {origin, duration, cities, interests, device_type}
            available_products: 可选的产品列表
        
        Returns:
            {recommendations, summary, estimated_roi} 或 None
        """
        if not self.available:
            logger.warning("LLM not available, falling back to rules")
            return None
        
        # 默认产品列表
        if available_products is None:
            available_products = [
                {"name": "eSIM 10GB/15days", "provider": "Airalo", "price": "$12", "url": "..."},
                {"name": "VPN 1 Month", "provider": "Affiliatescn", "price": "$7.50", "url": "..."},
                {"name": "Travel Insurance 14 days", "provider": "SafetyWing", "price": "$36", "url": "..."},
                {"name": "Hotels", "provider": "Booking.com", "price": "Variable", "url": "..."},
                {"name": "Tours", "provider": "Klook", "price": "From $30", "url": "..."}
            ]
        
        products_text = json.dumps(available_products, ensure_ascii=False, indent=2)
        
        prompt = COMMERCE_PERSONALIZE_PROMPT.format(
            origin=user_context.get('origin', 'Unknown'),
            duration=user_context.get('duration', 'Unknown'),
            cities=', '.join(user_context.get('cities', [])) or 'Not specified',
            interests=', '.join(user_context.get('interests', [])) or 'Not specified',
            device_type=user_context.get('device_type', 'Unknown'),
            products=products_text
        )
        
        result = self.llm.chat(
            prompt,
            system_prompt="You are a personalized travel affiliate recommendation engine. Return JSON only, no markdown, max 5 recommendations.",
            max_tokens=3000,
            temperature=0.7
        )
        
        if not result:
            return None
        
        # 解析 JSON
        parsed = _parse_json_response(result['content'])
        if not parsed:
            logger.warning("Failed to parse Commerce LLM response: %s", result['content'][:500])
            return None
        return parsed
    
    def analyze_user_intent(
        self,
        behavior: dict
    ) -> Optional[dict]:
        """User Agent: LLM 用户意图分析
        
        Args:
            behavior: {actions, session_duration, pages_visited, current_page, device_type, traffic_source}
        
        Returns:
            {primary_intent, intent_confidence, predicted_next_action, ...} 或 None
        """
        if not self.available:
            logger.warning("LLM not available, falling back to rules")
            return None
        
        prompt = USER_INTENT_PROMPT.format(
            actions=', '.join(behavior.get('actions', [])) or 'No actions recorded',
            session_duration=behavior.get('session_duration', 0),
            pages_visited=behavior.get('pages_visited', 0),
            current_page=behavior.get('current_page', 'Unknown'),
            device_type=behavior.get('device_type', 'Unknown'),
            traffic_source=behavior.get('traffic_source', 'Unknown')
        )
        
        result = self.llm.chat(
            prompt,
            system_prompt="You are a user intent analysis engine. Always return valid JSON only, no markdown.",
            max_tokens=1000,
            temperature=0.5
        )
        
        if not result:
            return None
        
        # 解析 JSON
        parsed = _parse_json_response(result['content'])
        if not parsed:
            logger.warning("Failed to parse User Intent LLM response: %s", result['content'][:500])
            return None
        return parsed
    
    def generate_cta_variants(
        self,
        article_context: dict
    ) -> Optional[dict]:
        """Conversion Agent: LLM CTA 变体生成
        
        Args:
            article_context: {article_type, topic, audience, current_cta}
        
        Returns:
            {variants, recommended_variant, a_b_test_design} 或 None
        """
        if not self.available:
            logger.warning("LLM not available, falling back to rules")
            return None
        
        prompt = CONVERSION_CTA_PROMPT.format(
            article_type=article_context.get('article_type', 'guide'),
            topic=article_context.get('topic', 'China travel'),
            audience=article_context.get('audience', 'general'),
            current_cta=article_context.get('current_cta', 'No current CTA')
        )
        
        result = self.llm.chat(
            prompt,
            system_prompt="You are a conversion optimization copywriter. Always return valid JSON.",
            max_tokens=800,
            temperature=0.8
        )
        
        if not result:
            return None
        
        # 解析 JSON
        parsed = _parse_json_response(result['content'])
        if not parsed:
            logger.warning("Failed to parse Conversion LLM response: %s", result['content'][:200])
            return None
        return parsed
    
    def analyze_revenue_trends(
        self,
        revenue_data: dict,
        traffic_data: dict
    ) -> Optional[dict]:
        """Revenue Agent: LLM 营收洞察
        
        Args:
            revenue_data: {period, total_revenue, affiliate_clicks, conversion_rate, aov, top_categories}
            traffic_data: {total_visits, pages_per_visit, bounce_rate, organic_traffic, direct_traffic}
        
        Returns:
            {trend, growth_rate, revenue_per_visitor, top_opportunities, risks, recommendations, summary} 或 None
        """
        if not self.available:
            logger.warning("LLM not available, falling back to rules")
            return None
        
        prompt = REVENUE_INSIGHT_PROMPT.format(
            period=revenue_data.get('period', 'Monthly'),
            total_revenue=revenue_data.get('total_revenue', 0),
            affiliate_clicks=revenue_data.get('affiliate_clicks', 0),
            conversion_rate=revenue_data.get('conversion_rate', 0),
            aov=revenue_data.get('aov', 0),
            top_categories=', '.join(revenue_data.get('top_categories', [])) or 'No data',
            total_visits=traffic_data.get('total_visits', 0),
            pages_per_visit=traffic_data.get('pages_per_visit', 0),
            bounce_rate=traffic_data.get('bounce_rate', 0),
            organic_traffic=traffic_data.get('organic_traffic', 0),
            direct_traffic=traffic_data.get('direct_traffic', 0)
        )
        
        result = self.llm.chat(
            prompt,
            system_prompt="You are a revenue analytics engine. Return JSON only, no markdown, max 3 opportunities and 2 risks.",
            max_tokens=3000,
            temperature=0.5
        )
        
        if not result:
            return None
        
        # 解析 JSON
        parsed = _parse_json_response(result['content'])
        if not parsed:
            logger.warning("Failed to parse Revenue LLM response: %s", result['content'][:500])
            return None
        return parsed


# ============ 便捷函数 ============

_enhancer_instance: Optional[LLMEnhancer] = None

def get_enhancer() -> LLMEnhancer:
    """获取 LLMEnhancer 单例"""
    global _enhancer_instance
    if _enhancer_instance is None:
        _enhancer_instance = LLMEnhancer()
    return _enhancer_instance


# ============ 测试入口 ============

if __name__ == '__main__':
    print("🧪 LLM Agent Enhancer Test")
    print("=" * 50)
    
    enhancer = LLMEnhancer()
    
    print(f"\nLLM Available: {enhancer.available}")
    
    if enhancer.available:
        # Test 1: Commerce Personalization
        print("\n--- Test 1: Commerce Personalization ---")
        result = enhancer.personalize_affiliate({
            "origin": "USA",
            "duration": "10 days",
            "cities": ["Beijing", "Shanghai"],
            "interests": ["Food", "History"]
        })
        if result:
            print(f"✓ {len(result.get('recommendations', []))} recommendations")
            print(f"  Summary: {result.get('summary', 'N/A')}")
        else:
            print("✗ Failed")
        
        # Test 2: User Intent
        print("\n--- Test 2: User Intent Analysis ---")
        result = enhancer.analyze_user_intent({
            "actions": ["read_visa_article", "clicked_esim_link", "added_to_cart"],
            "session_duration": 300,
            "pages_visited": 3,
            "current_page": "/esim-guide",
            "device_type": "mobile",
            "traffic_source": "organic"
        })
        if result:
            print(f"✓ Intent: {result.get('primary_intent', 'N/A')}")
            print(f"  Confidence: {result.get('intent_confidence', 'N/A')}")
        else:
            print("✗ Failed")
        
        # Test 3: Conversion CTA
        print("\n--- Test 3: Conversion CTA Variants ---")
        result = enhancer.generate_cta_variants({
            "article_type": "payment_guide",
            "topic": "Alipay vs WeChat Pay",
            "audience": "first_time_visitors",
            "current_cta": "Download Free Guide"
        })
        if result:
            print(f"✓ {len(result.get('variants', []))} variants generated")
            for v in result.get('variants', []):
                print(f"  [{v.get('style')}] {v.get('cta_text', 'N/A')[:50]}...")
        else:
            print("✗ Failed")
        
        # Test 4: Revenue Insights
        print("\n--- Test 4: Revenue Insights ---")
        result = enhancer.analyze_revenue_trends(
            revenue_data={
                "period": "September 2026",
                "total_revenue": 2500,
                "affiliate_clicks": 500,
                "conversion_rate": 4.2,
                "aov": 50,
                "top_categories": ["esim", "vpn", "insurance"]
            },
            traffic_data={
                "total_visits": 15000,
                "pages_per_visit": 3.2,
                "bounce_rate": 45,
                "organic_traffic": 70,
                "direct_traffic": 15
            }
        )
        if result:
            print(f"✓ Trend: {result.get('trend', 'N/A')}")
            print(f"  Summary: {result.get('summary', 'N/A')[:100]}...")
        else:
            print("✗ Failed")
    
    print("\n✅ Test completed!")
