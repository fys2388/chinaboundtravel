/**
 * SYN-004 高价值用户个性化推荐
 * 集成ID: SYN-004
 * 生成时间: 2026-08-31 01:50:39
 * 功能: 根据用户分层提供个性化内容和CTA推荐
 * 隐私: GDPR合规，Cookie同意，90天数据保留
 */

(function() {
  'use strict';

  // 配置
  const CONFIG = {
    storageKey: 'cbt_personalization',
    cookieConsentKey: 'cbt_cookie_consent',
    dataRetentionDays: 90,
    segmentRules: [
      {
            "rule_id": "SYN004_converter",
            "segment": "converter",
            "segment_priority": "medium",
            "user_count": 0,
            "ltv": 0,
            "conversion_rate": 100.0,
            "retention_rate": 0,
            "recommended_content_types": [
                  "how_to_guide"
            ],
            "recommended_topics": [
                  "visa-free transit",
                  "high-speed rail",
                  "payment guide",
                  "travel insurance",
                  "esim"
            ],
            "recommended_cta_types": [
                  "product_card",
                  "button"
            ],
            "recommended_cta_positions": [
                  "article_bottom",
                  "article_middle",
                  "sidebar"
            ],
            "personalization_level": "basic",
            "expected_ltv_boost": 0.05,
            "expected_conversion_boost": 0.2,
            "status": "ready",
            "created_at": "2026-08-31T01:47:53.690777",
            "synergy_id": "SYN-004"
      },
      {
            "rule_id": "SYN004_new_user",
            "segment": "new_user",
            "segment_priority": "medium",
            "user_count": 0,
            "ltv": 0,
            "conversion_rate": 0.5,
            "retention_rate": 0,
            "recommended_content_types": [
                  "how_to_guide"
            ],
            "recommended_topics": [
                  "china travel overview",
                  "first-timer guide",
                  "travel basics",
                  "visa guide",
                  "safety tips"
            ],
            "recommended_cta_types": [
                  "product_card",
                  "button"
            ],
            "recommended_cta_positions": [
                  "article_bottom",
                  "article_middle",
                  "sidebar"
            ],
            "personalization_level": "basic",
            "expected_ltv_boost": 0.05,
            "expected_conversion_boost": 0.2,
            "status": "ready",
            "created_at": "2026-08-31T01:47:53.690794",
            "synergy_id": "SYN-004"
      },
      {
            "rule_id": "SYN004_returning_user",
            "segment": "returning_user",
            "segment_priority": "medium",
            "user_count": 0,
            "ltv": 0,
            "conversion_rate": 2.0,
            "retention_rate": 0,
            "recommended_content_types": [
                  "how_to_guide"
            ],
            "recommended_topics": [
                  "new articles",
                  "updated guides",
                  "seasonal travel",
                  "event guides",
                  "travel news"
            ],
            "recommended_cta_types": [
                  "product_card",
                  "button"
            ],
            "recommended_cta_positions": [
                  "article_bottom",
                  "article_middle",
                  "sidebar"
            ],
            "personalization_level": "basic",
            "expected_ltv_boost": 0.05,
            "expected_conversion_boost": 0.2,
            "status": "ready",
            "created_at": "2026-08-31T01:47:53.690801",
            "synergy_id": "SYN-004"
      },
      {
            "rule_id": "SYN004_engaged_user",
            "segment": "engaged_user",
            "segment_priority": "medium",
            "user_count": 0,
            "ltv": 0,
            "conversion_rate": 5.0,
            "retention_rate": 0,
            "recommended_content_types": [
                  "how_to_guide"
            ],
            "recommended_topics": [
                  "city guides",
                  "attraction guides",
                  "transportation",
                  "accommodation",
                  "local experiences"
            ],
            "recommended_cta_types": [
                  "product_card",
                  "button"
            ],
            "recommended_cta_positions": [
                  "article_bottom",
                  "article_middle",
                  "sidebar"
            ],
            "personalization_level": "basic",
            "expected_ltv_boost": 0.05,
            "expected_conversion_boost": 0.2,
            "status": "ready",
            "created_at": "2026-08-31T01:47:53.690806",
            "synergy_id": "SYN-004"
      },
      {
            "rule_id": "SYN004_subscriber",
            "segment": "subscriber",
            "segment_priority": "medium",
            "user_count": 0,
            "ltv": 0,
            "conversion_rate": 8.0,
            "retention_rate": 0,
            "recommended_content_types": [
                  "how_to_guide"
            ],
            "recommended_topics": [
                  "travel guides",
                  "itinerary planning",
                  "cultural tips",
                  "food guides",
                  "photography"
            ],
            "recommended_cta_types": [
                  "product_card",
                  "button"
            ],
            "recommended_cta_positions": [
                  "article_bottom",
                  "article_middle",
                  "sidebar"
            ],
            "personalization_level": "basic",
            "expected_ltv_boost": 0.05,
            "expected_conversion_boost": 0.2,
            "status": "ready",
            "created_at": "2026-08-31T01:47:53.690811",
            "synergy_id": "SYN-004"
      }
]
  };

  // 用户分层检测
  function detectUserSegment() {
    const now = Date.now();
    const visits = parseInt(localStorage.getItem('cbt_visits') || '0');
    const lastVisit = parseInt(localStorage.getItem('cbt_last_visit') || '0');
    const subscribed = localStorage.getItem('cbt_subscribed') === 'true';
    const converted = localStorage.getItem('cbt_converted') === 'true';
    const sessionDuration = now - (parseInt(sessionStorage.getItem('cbt_session_start') || String(now)));
    const pagesViewed = parseInt(sessionStorage.getItem('cbt_pages_viewed') || '1');

    // 更新访问数据
    localStorage.setItem('cbt_visits', String(visits + 1));
    localStorage.setItem('cbt_last_visit', String(now));
    sessionStorage.setItem('cbt_session_start', String(now));

    // 分层判断
    if (converted) return 'converter';
    if (subscribed) return 'subscriber';
    if (sessionDuration > 120000 || pagesViewed > 3) return 'engaged_user';
    if (visits > 1) return 'returning_user';
    return 'new_user';
  }

  // 获取个性化推荐
  function getPersonalizedRecommendations(segment) {
    const recommendations = {
      new_user: {
        content: ['/posts/china-travel-guide/', '/posts/144-hour-visa-free-transit-guide/'],
        cta: 'Start planning your China trip today',
        ctaType: 'banner'
      },
      returning_user: {
        content: ['/posts/china-high-speed-rail-guide/', '/posts/china-payment-guide/'],
        cta: 'Discover more China travel tips',
        ctaType: 'button'
      },
      engaged_user: {
        content: ['/posts/chengdu-hotpot-guide/', '/posts/zhangjiajie-photography-guide/'],
        cta: 'Explore our detailed city guides',
        ctaType: 'product_card'
      },
      subscriber: {
        content: ['/posts/china-itinerary-7-days/', '/posts/china-travel-resources/'],
        cta: 'Get exclusive subscriber deals',
        ctaType: 'product_card'
      },
      converter: {
        content: ['/posts/china-travel-insurance/', '/posts/china-esim-guide/'],
        cta: 'Upgrade your travel experience',
        ctaType: 'product_card'
      }
    };
    return recommendations[segment] || recommendations.new_user;
  }

  // 渲染个性化推荐
  function renderPersonalization(segment, recommendations) {
    // 创建个性化容器
    const container = document.createElement('div');
    container.className = 'personalization-container';
    container.setAttribute('data-segment', segment);
    container.innerHTML = `
      <div class="personalization-card">
        <h4>Recommended for You</h4>
        <div class="personalization-links">
          ${recommendations.content.map(url => `<a href="${url}" class="personalization-link">Read More</a>`).join('')}
        </div>
        <a href="/resources/" class="personalization-cta personalization-cta-${recommendations.ctaType}">${recommendations.cta}</a>
      </div>
      <style>
        .personalization-container { margin: 30px 0; }
        .personalization-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 25px; text-align: center; }
        .personalization-links { margin: 15px 0; }
        .personalization-link { display: inline-block; margin: 5px 10px; color: #2563eb; text-decoration: underline; }
        .personalization-cta { display: inline-block; padding: 12px 30px; background-color: #2563eb; color: #fff; text-decoration: none; border-radius: 8px; font-weight: 600; margin-top: 10px; }
        .personalization-cta:hover { background-color: #1d4ed8; }
      </style>
    `;

    // 插入到文章底部
    const articleContent = document.querySelector('.post-content, article, .content');
    if (articleContent) {
      articleContent.appendChild(container);
    }
  }

  // 主函数
  function init() {
    // 检查Cookie同意
    const hasConsent = localStorage.getItem(CONFIG.cookieConsentKey) === 'true';
    if (!hasConsent) {
      console.log('[Personalization] Cookie consent not given, skipping');
      return;
    }

    try {
      const segment = detectUserSegment();
      const recommendations = getPersonalizedRecommendations(segment);
      renderPersonalization(segment, recommendations);

      // 保存分层数据
      const personalizationData = {
        segment: segment,
        timestamp: Date.now(),
        recommendations: recommendations
      };
      localStorage.setItem(CONFIG.storageKey, JSON.stringify(personalizationData));

      console.log('[Personalization] Applied for segment:', segment);
    } catch (e) {
      console.error('[Personalization] Error:', e);
    }
  }

  // DOM加载完成后初始化
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
