/*
  项目级覆盖 themes/PaperMod/assets/js/fastsearch.js。

  实测（2026-09-20，客户视角走查）：首页主 CTA「🗺️ Plan Your China Trip」
  指向 /search/。客户点进来看到的是一个空搜索框 ——
  - 无默认内容，无输入提示语（主题只有 input 的 placeholder）
  - 输入不存在的关键字 -> renderResults([]) 只是把列表清空，页面上一片空白
  - index.json 加载失败 -> 只 console.error，客户面对一个永久空框，
    不知道是「没结果」还是「坏了」

  一个客户从这个入口进来，3 秒内看不到任何东西，就会关掉标签页。
  首页 CTA 的转化率就死在这里。

  本覆盖版加三件事：空状态引导语、无结果建议、加载失败显式提示。
  其余逻辑与主题版完全一致。
*/
import * as params from '@params';

const resList = document.getElementById('searchResults');
const sInput = document.getElementById('searchInput');
const searchBox = document.getElementById('searchbox');

let fuse;
let fuseReady = false;
let currentElement = null;
let firstResult = null;
let lastResult = null;

const defaultFuseOptions = {
    distance: 100,
    threshold: 0.4,
    ignoreLocation: true,
    keys: ['title', 'permalink', 'summary', 'content']
};

const buildFuseOptions = () => {
    if (!params.fuseOpts) {
        return defaultFuseOptions;
    }

    return {
        isCaseSensitive: params.fuseOpts.iscasesensitive ?? false,
        includeScore: params.fuseOpts.includescore ?? false,
        includeMatches: params.fuseOpts.includematches ?? false,
        minMatchCharLength: params.fuseOpts.minmatchcharlength ?? 1,
        shouldSort: params.fuseOpts.shouldsort ?? true,
        findAllMatches: params.fuseOpts.findallmatches ?? false,
        keys: params.fuseOpts.keys ?? defaultFuseOptions.keys,
        location: params.fuseOpts.location ?? 0,
        threshold: params.fuseOpts.threshold ?? defaultFuseOptions.threshold,
        distance: params.fuseOpts.distance ?? defaultFuseOptions.distance,
        ignoreLocation: params.fuseOpts.ignorelocation ?? defaultFuseOptions.ignoreLocation
    };
};

const debounce = (fn, delay) => {
    let timeout;
    return (...args) => {
        clearTimeout(timeout);
        timeout = window.setTimeout(() => fn(...args), delay);
    };
};

/* ── 空状态 / 无结果 / 失败提示（主题版完全没有） ─────────────────── */

// 首页 CTA 直接指向本页，客户进来第一眼必须有东西可看。
const EMPTY_HINT =
    'Type above to search our China travel guides — ' +
    'visa, Alipay, eSIM, trains, city guides…';

// 无结果时给 5 个真实存在的高频主题，避免客户死路一条。
const SUGGESTED = ['visa', 'Alipay', 'eSIM', 'high-speed train', 'Shanghai'];

const showHint = () => {
    resList.innerHTML =
        '<li class="search-empty" role="status">' +
        EMPTY_HINT + '</li>';
};

const showNoResults = (query) => {
    const chips = SUGGESTED.map((t) =>
        '<button type="button" class="search-suggest" data-q="' + t + '">' + t + '</button>'
    ).join(' ');
    resList.innerHTML =
        '<li class="search-empty" role="status">' +
        'No guides found for “<strong>' + escapeHtml(query) + '”.</strong>' +
        ' Try one of these:' + chips +
        '</li>';
    resList.querySelectorAll('.search-suggest').forEach((b) => {
        b.addEventListener('click', () => {
            sInput.value = b.dataset.q;
            performSearch();
        });
    });
};

const showLoadError = () => {
    resList.innerHTML =
        '<li class="search-empty search-error" role="status">' +
        'Search is temporarily unavailable. Browse <a href="/categories/">all guides</a> ' +
        'instead, or try again in a few minutes.' +
        '</li>';
};

const escapeHtml = (s) => String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');

const clearResults = () => {
    resList.innerHTML = '';
    firstResult = lastResult = currentElement = null;
};

const reset = () => {
    clearResults();
    sInput.value = '';
    sInput.focus();
    if (fuseReady) showHint();
};

const setActiveResult = (element) => {
    document.querySelectorAll('.focus').forEach((item) => item.classList.remove('focus'));

    if (!element) {
        return;
    }

    element.focus();
    element.parentElement?.classList.add('focus');
    currentElement = element;
};

const renderResults = (results) => {
    clearResults();

    if (!Array.isArray(results) || results.length === 0) {
        // 有查询无结果 -> 给建议；空查询 -> 给引导语。
        if (sInput.value.trim()) showNoResults(sInput.value.trim());
        else showHint();
        return;
    }

    const fragment = document.createDocumentFragment();

    for (const result of results) {
        const li = document.createElement('li');
        const titleText = document.createTextNode(result.item.title);
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', '24');
        svg.setAttribute('height', '24');
        svg.setAttribute('viewBox', '0 0 24 24');
        svg.setAttribute('fill', 'none');
        svg.setAttribute('stroke', 'currentColor');
        svg.setAttribute('stroke-width', '2');
        svg.setAttribute('stroke-linecap', 'round');
        svg.setAttribute('stroke-linejoin', 'round');
        svg.classList.add('feather', 'feather-chevrons-right');

        svg.innerHTML = '<polyline points="13 17 18 12 13 7"></polyline><polyline points="6 17 11 12 6 7"></polyline>';

        const link = document.createElement('a');
        link.className = 'entry-link';
        link.href = result.item.permalink;
        link.setAttribute('aria-label', result.item.title);

        li.appendChild(titleText);
        li.appendChild(svg);
        li.appendChild(link);
        fragment.appendChild(li);
    }

    resList.appendChild(fragment);
    firstResult = resList.firstElementChild;
    lastResult = resList.lastElementChild;
};

const performSearch = () => {
    if (!fuse) {
        return;
    }

    const query = sInput.value.trim();
    if (!query) {
        renderResults([]);
        return;
    }

    const searchOptions = params.fuseOpts?.limit ? { limit: params.fuseOpts.limit } : undefined;
    const results = searchOptions ? fuse.search(query, searchOptions) : fuse.search(query);
    renderResults(results);
};

const initSearch = async () => {
    if (!sInput || !resList) {
        return;
    }

    sInput.disabled = false;
    sInput.focus();

    try {
        const response = await fetch('../index.json');
        if (!response.ok) {
            throw new Error(`Search index load failed: ${response.status}`);
        }

        const data = await response.json();
        if (data) {
            fuse = new Fuse(data, buildFuseOptions());
            fuseReady = true;
        } else {
            throw new Error('Search index is empty');
        }
        showHint();
    } catch (error) {
        console.error(error);
        // 主题版到这里就静默了 —— 客户面对一个永久空框，分不清是没结果还是坏了。
        showLoadError();
    }
};

window.addEventListener('load', initSearch);

sInput?.addEventListener('input', debounce(performSearch, 150));

sInput?.addEventListener('search', () => {
    if (!sInput.value) {
        reset();
    }
});

document.addEventListener('keydown', (event) => {
    const { key } = event;
    const active = document.activeElement;
    const isInSearchBox = searchBox?.contains(active);

    if (key === 'Escape') {
        reset();
        return;
    }

    if (!firstResult || !isInSearchBox) {
        return;
    }

    if (key === 'ArrowDown') {
        event.preventDefault();

        if (active === sInput) {
            setActiveResult(firstResult.querySelector('.entry-link'));
        } else if (active?.parentElement !== lastResult) {
            setActiveResult(active?.parentElement?.nextElementSibling?.querySelector('.entry-link'));
        }
    } else if (key === 'ArrowUp') {
        event.preventDefault();

        if (active?.parentElement === firstResult) {
            setActiveResult(sInput);
        } else if (active !== sInput) {
            setActiveResult(active?.parentElement?.previousElementSibling?.querySelector('.entry-link'));
        }
    } else if (key === 'ArrowRight') {
        if (active?.matches?.('.entry-link')) {
            active.click();
        }
    }
});
