/**
 * A/B Test Runner - Lightweight Experiment Framework
 * 加载 /experiments.json，匹配当前页面，随机分配变体，上报 GA4 事件
 * 用法：在 Hugo baseof.html 中引入 <script src="/js/ab-runner.js" defer></script>
 */
(function () {
  'use strict';

  const STORAGE_KEY = 'ab_experiments_v1';
  const CONFIG_URL = '/experiments.json';

  // 安全获取 localStorage
  function getStorage() {
    try { return localStorage.getItem(STORAGE_KEY); } catch (e) { return null; }
  }
  function setStorage(data) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(data)); } catch (e) {}
  }

  // 读取已分配的变体
  function getAssignments() {
    try {
      const raw = getStorage();
      return raw ? JSON.parse(raw) : {};
    } catch (e) { return {}; }
  }

  // 随机分配变体（按 traffic 权重）
  function assignVariant(variants) {
    const total = variants.reduce((s, v) => s + (v.traffic || 0), 0);
    if (total <= 0) return variants[0];
    let r = Math.random() * total;
    for (const v of variants) {
      r -= (v.traffic || 0);
      if (r <= 0) return v;
    }
    return variants[variants.length - 1];
  }

  // 匹配当前页面
  function matchPage(pattern) {
    try {
      return new RegExp(pattern, 'i').test(window.location.pathname);
    } catch (e) {
      return false;
    }
  }

  // 上报 GA4 事件
  function trackEvent(name, params) {
    try {
      if (window.gtag) {
        window.gtag('event', name, params);
      } else if (window.dataLayer) {
        window.dataLayer.push({ event: name, ...params });
      }
    } catch (e) {}
  }

  // 应用变体到 DOM
  function applyVariant(exp, variant) {
    // 给 body 添加实验 class，供 CSS 控制
    document.body.classList.add(`ab-${exp.id}-${variant.id}`);
    document.body.setAttribute(`data-ab-${exp.id}`, variant.id);

    // 查找带 data-ab 属性的元素并替换内容
    const elements = document.querySelectorAll(`[data-ab="${exp.id}"]`);
    elements.forEach(el => {
      const elementName = el.getAttribute('data-ab-element') || 'default';
      const variantContent = variant.content && variant.content[elementName];
      if (variantContent) {
        if (variantContent.text) el.textContent = variantContent.text;
        if (variantContent.html) el.innerHTML = variantContent.html;
        if (variantContent.href) el.setAttribute('href', variantContent.href);
        if (variantContent.class) el.classList.add(variantContent.class);
      }
    });

    // 监听目标事件（转化）
    if (exp.goal_event) {
      document.addEventListener('click', function (e) {
        const target = e.target.closest('[data-ab-goal]');
        if (target && target.getAttribute('data-ab-goal') === exp.id) {
          trackEvent('experiment_conversion', {
            experiment_id: exp.id,
            experiment_name: exp.name,
            variant_id: variant.id,
            variant_name: variant.name,
            page_path: window.location.pathname
          });
        }
      }, { once: false });
    }
  }

  // 主流程
  async function init() {
    try {
      const resp = await fetch(CONFIG_URL, { cache: 'no-cache' });
      if (!resp.ok) return;
      const config = await resp.json();
      const experiments = config.experiments || [];
      const assignments = getAssignments();
      let changed = false;

      for (const exp of experiments) {
        // 只执行 RUNNING 状态的实验
        if (exp.status !== 'RUNNING') continue;
        if (!matchPage(exp.page_pattern)) continue;
        if (!exp.variants || exp.variants.length === 0) continue;

        // 获取或分配变体
        let assigned = assignments[exp.id];
        if (!assigned || !exp.variants.find(v => v.id === assigned.variant_id)) {
          const variant = assignVariant(exp.variants);
          assigned = {
            variant_id: variant.id,
            variant_name: variant.name,
            assigned_at: new Date().toISOString()
          };
          assignments[exp.id] = assigned;
          changed = true;
        }

        // 应用变体
        const variant = exp.variants.find(v => v.id === assigned.variant_id);
        if (variant) {
          applyVariant(exp, variant);

          // 上报实验曝光
          trackEvent('experiment_view', {
            experiment_id: exp.id,
            experiment_name: exp.name,
            variant_id: variant.id,
            variant_name: variant.name,
            page_path: window.location.pathname
          });
        }
      }

      if (changed) setStorage(assignments);
    } catch (e) {
      // 静默失败，不影响页面
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
