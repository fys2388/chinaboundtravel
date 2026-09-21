/**
 * Cloudflare Worker - AI Trip Planner API
 * 
 * 功能：
 * 1. 接收用户旅行参数（时间、天数、城市、兴趣）
 * 2. 调用 SenseNova LLM 生成个性化行程建议
 * 3. 返回相关文章推荐 + CTA
 * 
 * 端点：POST /api/trip-plan
 * 
 * @author Joran - ChinaBound Travel
 * @version 1.0.0
 */

// ============ 配置 ============

const SENSENOVA_API_URL = 'https://token.sensenova.cn/v1/chat/completions';
const SENSENOVA_MODEL = 'sensenova-6.8-flash-lite';

// CORS Headers
const corsHeaders = () => ({
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  'Access-Control-Max-Age': '86400'
});

// 文章知识库（从 post_index.json 提取的核心文章）
const ARTICLE_KNOWLEDGE = [
  { slug: 'alipay-vs-wechat-pay', title: 'Alipay vs WeChat Pay for Tourists', cities: ['all'], category: 'payment' },
  { slug: 'china-visa-free-entry-2026', title: 'China Visa-Free Entry 2026', cities: ['all'], category: 'visa' },
  { slug: 'china-high-speed-rail-guide', title: 'China High-Speed Rail Guide', cities: ['all'], category: 'transport' },
  { slug: 'shanghai-vs-beijing', title: 'Shanghai vs Beijing: Which to Visit First', cities: ['Beijing', 'Shanghai'], category: 'comparison' },
  { slug: 'china-food-culture', title: 'Chinese Food Culture Guide', cities: ['all'], category: 'food' },
  { slug: 'china-national-parks', title: 'China National Parks: Zhangjiajie & Jiuzhaigou', cities: ['Zhangjiajie'], category: 'nature' },
  { slug: 'xian-terracotta-army', title: "Xi'an Terracotta Army Guide", cities: ["Xi'an"], category: 'history' },
  { slug: 'chinese-tea-culture', title: 'Chinese Tea Culture: Authentic Teahouses', cities: ['Chengdu', 'Hangzhou', 'all'], category: 'culture' },
  { slug: 'china-travel-etiquette', title: 'China Travel Etiquette: Tipping & Photos', cities: ['all'], category: 'etiquette' },
  { slug: 'china-packing-list-2026', title: 'China Packing List 2026', cities: ['all'], category: 'packing' },
  { slug: 'traveling-to-china-for-business', title: 'Traveling to China for Business', cities: ['Shanghai', 'Beijing', 'Guangzhou'], category: 'business' },
  { slug: 'china-esim-guide', title: 'eSIM & Internet in China', cities: ['all'], category: 'internet' }
];

// ============ Prompt 模板 ============

function buildTripPlanPrompt(params, articleContext) {
  const { trip_when, trip_duration, trip_cities, trip_interests } = params;
  
  // 根据城市和兴趣筛选相关文章
  let relevantArticles = ARTICLE_KNOWLEDGE.filter(a => {
    if (a.cities.includes('all')) return true;
    return trip_cities.some(c => a.cities.includes(c));
  });
  
  // 限制最多 8 篇
  relevantArticles = relevantArticles.slice(0, 8);
  
  const articlesText = relevantArticles.map(a => 
    `- ${a.title} (${a.category}): https://chinaboundtravel.com/posts/${a.slug}/`
  ).join('\n');
  
  return `You are Joran, the editorial voice of ChinaBound Travel, a trusted China travel guide website.

## User's Trip Details:
- When coming: ${trip_when || 'Not specified'}
- Duration: ${trip_duration || 'Not specified'}
- Cities interested: ${trip_cities.join(', ') || 'Not specified'}
- Interests: ${trip_interests.join(', ') || 'Not specified'}

## Current Article Context:
The user is reading: "${articleContext || 'A China travel article'}"

## Relevant ChinaBound Travel Guides:
${articlesText}

## Task:
Generate a personalized 200-word travel plan recommendation that:
1. Acknowledges their specific trip details
2. Gives practical day-by-day suggestions for their duration
3. Recommends 3-5 specific articles from the list above that they should read
4. Ends with a CTA to download the free itinerary template or subscribe for monthly updates

## Output Format:
Return JSON only:
{
  "summary": "Your 200-word personalized recommendation...",
  "recommended_articles": [
    {"title": "Article Title", "url": "https://chinaboundtravel.com/posts/slug/"},
    {"title": "Article Title", "url": "https://chinaboundtravel.com/posts/slug/"}
  ],
  "cta": "Download Free Itinerary Template | Subscribe for Monthly Updates"
}

IMPORTANT: Only return valid JSON. No markdown, no extra text.`;
}

// ============ 主处理函数 ============

export default {
  async fetch(request, env, ctx) {
    // CORS 预检
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

    const url = new URL(request.url);

    // 健康检查
    if (url.pathname === '/health') {
      return json({ status: 'ok', service: 'trip-planner' });
    }

    // 主端点：POST /api/trip-plan
    if (url.pathname === '/api/trip-plan' && request.method === 'POST') {
      try {
        const body = await request.json();
        return await handleTripPlan(body, env, ctx);
      } catch (e) {
        return json({ error: 'Invalid request', message: e.message }, 400);
      }
    }

    // Commerce Agent 端点：POST /api/commerce-recommend
    if (url.pathname === '/api/commerce-recommend' && request.method === 'POST') {
      try {
        const body = await request.json();
        return await handleCommerceRecommend(body, env, ctx);
      } catch (e) {
        return json({ error: 'Invalid request', message: e.message }, 400);
      }
    }

    // 404
    return json({ error: 'Not found' }, 404);
  }
};

// ============ 核心逻辑 ============

async function handleTripPlan(body, env, ctx) {
  const { trip_when, trip_duration, trip_cities, trip_interests, current_article } = body;

  // 验证参数
  if (!trip_cities || !Array.isArray(trip_cities) || trip_cities.length === 0) {
    return json({ error: 'Missing or invalid trip_cities' }, 400);
  }

  // 获取 API Key
  const apiKey = env.SENSENOVA_API_KEY;
  if (!apiKey) {
    return json({ error: 'SENSENOVA_API_KEY not configured' }, 500);
  }

  // 构建 Prompt
  const prompt = buildTripPlanPrompt(
    { trip_when, trip_duration, trip_cities, trip_interests },
    current_article
  );

  // 调用 SenseNova API
  const response = await fetch(SENSENOVA_API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`
    },
    body: JSON.stringify({
      model: SENSENOVA_MODEL,
      messages: [
        { role: 'system', content: 'You are a helpful travel planning assistant. Always return valid JSON.' },
        { role: 'user', content: prompt }
      ],
      temperature: 0.7,
      max_tokens: 1000
    })
  });

  if (!response.ok) {
    const err = await response.text();
    return json({ error: 'LLM API error', details: err }, 502);
  }

  const data = await response.json();
  const content = data.choices?.[0]?.message?.content || '{}';

  // 解析 LLM 输出
  let result;
  try {
    // 尝试解析 JSON（LLM 可能返回带 ```json 包裹的内容）
    const jsonMatch = content.match(/\{[\s\S]*\}/);
    result = JSON.parse(jsonMatch ? jsonMatch[0] : content);
  } catch (e) {
    // 解析失败，返回原始内容
    result = {
      summary: content,
      recommended_articles: [],
      cta: 'Download Free Itinerary Template'
    };
  }

  // 记录调用日志（可选：写入 KV）
  await logUsage(env, {
    timestamp: new Date().toISOString(),
    cities: trip_cities,
    duration: trip_duration,
    when: trip_when,
    tokens_used: data.usage?.total_tokens || 0
  });

  return json(result);
}

// ============ 工具函数 ============

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...corsHeaders()
    }
  });
}

async function logUsage(env, data) {
  if (!env.KV_STORE) return;
  
  const key = `trip-plan:${new Date().toISOString().split('T')[0]}`;
  const existing = await env.KV_STORE.get(key, 'json') || { count: 0, details: [] };
  
  existing.count += 1;
  existing.details.push(data);
  
  await env.KV_STORE.put(key, JSON.stringify(existing), {
    expirationTtl: 365 * 24 * 60 * 60 // 1 year
  });
}

// ============ Commerce Agent ============

// 联盟产品知识库
const AFFILIATE_PRODUCTS = {
  esim: {
    name: 'eSIM',
    provider: 'Airalo',
    description: 'Stay connected with local data plans',
    base_url: 'https://www.airalo.com',
    utm_source: 'chinaboundtravel',
    utm_medium: 'affiliate',
    recommendations: {
      'usa': { 
        plan: '10GB / 15 days', 
        price: '$12', 
        url: 'https://www.airalo.com/store/eSim/china-10gb-15days/?aff=chinaboundtravel' 
      },
      'europe': { 
        plan: '10GB / 15 days', 
        price: '$12', 
        url: 'https://www.airalo.com/store/eSim/china-10gb-15days/?aff=chinaboundtravel' 
      },
      'asia': { 
        plan: '5GB / 7 days', 
        price: '$8', 
        url: 'https://www.airalo.com/store/eSim/china-5gb-7days/?aff=chinaboundtravel' 
      }
    }
  },
  vpn: {
    name: 'VPN',
    provider: 'Affiliatescn',
    description: 'Bypass restrictions and stay secure',
    base_url: 'https://affiliatescn.com',
    utm_source: 'chinaboundtravel',
    utm_medium: 'affiliate',
    recommendations: {
      default: {
        plan: '1 Month / Unlimited Devices',
        price: '$7.50',
        url: 'https://affiliatescn.com/go/chinaboundtravel?product=china-1month'
      }
    }
  },
  insurance: {
    name: 'Travel Insurance',
    provider: 'SafetyWing',
    description: 'Comprehensive coverage for your trip',
    base_url: 'https://safetywing.com',
    utm_source: 'chinaboundtravel',
    utm_medium: 'affiliate',
    recommendations: {
      '≤3 days': { 
        plan: 'Nomad Insurance / 1 day', 
        price: '$2.50', 
        url: 'https://safetywing.com/travel-insurance/plan-nomad?ref=chinaboundtravel' 
      },
      '4-7 days': { 
        plan: 'Nomad Insurance / 7 days', 
        price: '$18', 
        url: 'https://safetywing.com/travel-insurance/plan-nomad?ref=chinaboundtravel' 
      },
      '8-14 days': { 
        plan: 'Nomad Insurance / 14 days', 
        price: '$36', 
        url: 'https://safetywing.com/travel-insurance/plan-nomad?ref=chinaboundtravel' 
      },
      '2+ weeks': { 
        plan: 'Nomad Insurance / 1 month', 
        price: '$64', 
        url: 'https://safetywing.com/travel-insurance/plan-nomad?ref=chinaboundtravel' 
      }
    }
  },
  hotel: {
    name: 'Hotels',
    provider: 'Booking.com',
    description: 'Best rates on trusted accommodations',
    base_url: 'https://booking.com',
    utm_source: 'chinaboundtravel',
    utm_medium: 'affiliate',
    recommendations: {
      default: {
        plan: 'Book Hotels & Homes',
        price: 'Free cancellation available',
        url: 'https://www.booking.com/searchresults.html?ss=China&aid=chinaboundtravel'
      }
    }
  },
  tour: {
    name: 'Tours & Tickets',
    provider: 'Klook',
    description: 'Skip the lines with prepaid tickets',
    base_url: 'https://klook.com',
    utm_source: 'chinaboundtravel',
    utm_medium: 'affiliate',
    recommendations: {
      'Beijing': {
        plan: 'Great Wall + Forbidden City Tour',
        price: 'From $45',
        url: 'https://www.klook.com/en-US/search/result/?q=china&t=chinaboundtravel'
      },
      'Shanghai': {
        plan: 'Shanghai Pudong Tour',
        price: 'From $35',
        url: 'https://www.klook.com/en-US/search/result/?q=shanghai&t=chinaboundtravel'
      },
      "Xi'an": {
        plan: 'Terracotta Warriors Tour',
        price: 'From $30',
        url: 'https://www.klook.com/en-US/search/result/?q=xian&t=chinaboundtravel'
      }
    }
  }
};

async function handleCommerceRecommend(body, env, ctx) {
  const { origin_country, trip_duration, trip_cities, device_type, needs } = body;
  
  // 尝试使用 LLM 个性化推荐
  const apiKey = env.SENSENOVA_API_KEY;
  if (apiKey) {
    try {
      return await handleCommerceRecommendLLM(body, apiKey, env);
    } catch (e) {
      console.error('LLM recommendation failed, falling back to rules:', e);
    }
  }
  
  // 规则推荐（降级）
  return handleCommerceRecommendRules(body, env);
}

async function handleCommerceRecommendLLM(body, apiKey, env) {
  const { origin_country, trip_duration, trip_cities } = body;
  
  const prompt = `User: ${origin_country || 'Unknown'}, ${trip_duration || 'Unknown'} days, cities: ${trip_cities?.join(',') || 'Not specified'}, interests: ${body.interests?.join(',') || 'Not specified'}

Products: [
  {"name":"eSIM 10GB","provider":"Airalo","price":"$12","url":"https://www.airalo.com/store/eSim/china-10gb-15days/?aff=chinaboundtravel"},
  {"name":"VPN 1 Month","provider":"Affiliatescn","price":"$7.50","url":"https://affiliatescn.com/go/chinaboundtravel?product=china-1month"},
  {"name":"Travel Insurance","provider":"SafetyWing","price":"$36","url":"https://safetywing.com/travel-insurance/plan-nomad?ref=chinaboundtravel"},
  {"name":"Hotels","provider":"Booking.com","price":"Variable","url":"https://www.booking.com/searchresults.html?ss=China&aid=chinaboundtravel"},
  {"name":"Tours","provider":"Klook","price":"From $30","url":"https://www.klook.com/en-US/search/result/?q=china&t=chinaboundtravel"}
]

Return JSON with max 3 recommendations:
{"recommendations":[{"name":"...","provider":"...","price":"...","url":"...","reason":"...","urgency":1-10}],"summary":"...","roi":"low|medium|high"}

JSON only, no markdown.`;

  const response = await fetch(SENSENOVA_API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`
    },
    body: JSON.stringify({
      model: SENSENOVA_MODEL,
      messages: [
        { role: 'system', content: 'You are a travel affiliate recommendation engine. Return JSON only.' },
        { role: 'user', content: prompt }
      ],
      temperature: 0.7,
      max_tokens: 2000
    })
  });

  if (!response.ok) {
    throw new Error('LLM API error');
  }

  const data = await response.json();
  const content = data.choices?.[0]?.message?.content || '{}';

  // 解析 JSON
  let result;
  try {
    const jsonMatch = content.match(/\{[\s\S]*\}/);
    result = JSON.parse(jsonMatch ? jsonMatch[0] : content);
  } catch (e) {
    throw new Error('Failed to parse LLM response');
  }

  // 记录日志
  if (env.KV_STORE) {
    const key = `commerce-llm:${new Date().toISOString().split('T')[0]}`;
    const existing = await env.KV_STORE.get(key, 'json') || { count: 0, details: [] };
    existing.count += 1;
    existing.details.push({
      timestamp: new Date().toISOString(),
      origin_country,
      trip_duration,
      trip_cities,
      tokens_used: data.usage?.total_tokens || 0
    });
    await env.KV_STORE.put(key, JSON.stringify(existing), {
      expirationTtl: 365 * 24 * 60 * 60
    });
  }

  return json({
    recommendations: result.recommendations || [],
    summary: result.summary,
    estimated_roi: result.roi,
    total_count: (result.recommendations || []).length,
    affiliate_disclosure: true,
    disclaimer: 'Some links are affiliate links. We may earn a commission at no extra cost to you.',
    llm_powered: true
  });
}

async function handleCommerceRecommendRules(body, env) {
  const { origin_country, trip_duration, trip_cities, device_type, needs } = body;
  
  // 默认推荐：所有用户都需要
  const recommendations = [];
  
  // 1. eSIM - 所有用户都需要
  const esimRegion = origin_country || 'asia';
  const esimPlan = AFFILIATE_PRODUCTS.esim.recommendations[esimRegion] || AFFILIATE_PRODUCTS.esim.recommendations.asia;
  recommendations.push({
    category: 'esim',
    name: `eSIM - ${esimPlan.plan}`,
    provider: 'Airalo',
    price: esimPlan.price,
    url: esimPlan.url,
    reason: 'Stay connected from the moment you land'
  });
  
  // 2. VPN - 根据设备类型
  if (device_type || true) { // 默认推荐
    const vpnPlan = AFFILIATE_PRODUCTS.vpn.recommendations.default;
    recommendations.push({
      category: 'vpn',
      name: `VPN - ${vpnPlan.plan}`,
      provider: 'Affiliatescn',
      price: vpnPlan.price,
      url: vpnPlan.url,
      reason: 'Bypass internet restrictions and stay secure'
    });
  }
  
  // 3. Travel Insurance - 根据行程时长
  const insurancePlan = AFFILIATE_PRODUCTS.insurance.recommendations[trip_duration] || AFFILIATE_PRODUCTS.insurance.recommendations['4-7 days'];
  recommendations.push({
    category: 'insurance',
    name: `Travel Insurance - ${insurancePlan.plan}`,
    provider: 'SafetyWing',
    price: insurancePlan.price,
    url: insurancePlan.url,
    reason: 'Comprehensive coverage for peace of mind'
  });
  
  // 4. Hotels - 根据城市
  if (trip_cities && trip_cities.length > 0) {
    const firstCity = trip_cities[0];
    recommendations.push({
      category: 'hotel',
      name: `Hotels in ${firstCity}`,
      provider: 'Booking.com',
      price: 'Free cancellation available',
      url: `https://www.booking.com/searchresults.html?ss=${encodeURIComponent(firstCity)}&aid=chinaboundtravel`,
      reason: `Best rates for ${firstCity} accommodations`
    });
  }
  
  // 5. Tours - 根据城市
  if (trip_cities && trip_cities.length > 0) {
    for (const city of trip_cities.slice(0, 2)) {
      const tourPlan = AFFILIATE_PRODUCTS.tour.recommendations[city];
      if (tourPlan) {
        recommendations.push({
          category: 'tour',
          name: `Tours - ${tourPlan.plan}`,
          provider: 'Klook',
          price: tourPlan.price,
          url: tourPlan.url,
          reason: `Skip the lines in ${city}`
        });
      }
    }
  }
  
  // 记录推荐日志
  if (env.KV_STORE) {
    const key = `commerce:${new Date().toISOString().split('T')[0]}`;
    const existing = await env.KV_STORE.get(key, 'json') || { count: 0, details: [] };
    existing.count += 1;
    existing.details.push({
      timestamp: new Date().toISOString(),
      origin_country,
      trip_duration,
      trip_cities,
      needs,
      recommended_categories: recommendations.map(r => r.category)
    });
    await env.KV_STORE.put(key, JSON.stringify(existing), {
      expirationTtl: 365 * 24 * 60 * 60
    });
  }
  
  return json({
    recommendations,
    total_count: recommendations.length,
    affiliate_disclosure: true,
    disclaimer: 'Some links are affiliate links. We may earn a commission at no extra cost to you.'
  });
}
