/**
 * Cloudflare Worker - Buffer GraphQL API Auto-Poster
 * 
 * 功能：
 * 1. 双Buffer账户分流：Buffer-A(FB+IG+X) / Buffer-B(Pinterest)
 * 2. 封面强校验：仅允许本站CDN图片
 * 3. 双层限流：全局单日≤2篇，各账户15min≤70次
 * 4. 429处理：指数退避+KV重试队列
 * 5. 配额预警：剩余≤30%飞书通知
 * 
 * @author Joran - ChinaBoundTravel
 * @version 3.0.0
 */

// ============ 配置常量 ============

/**
 * 双Buffer账户配置
 * Buffer-A：FB+IG+X，Buffer-B：独立Pinterest
 */
const BUFFER_ACCOUNTS = {
  A: {
    tokenKey: 'BUFFER_WORKER_URL',
    name: 'Buffer-A',
    channels: {
      x: { id: '6a202882c687a22dd45735b6', name: 'fys2388', service: 'twitter' },
      facebook: { id: '6a17e0c4c687a22dd4346d3c', name: 'ChinaBound Travel', service: 'facebook' },
      instagram: { id: '6a17e14dc687a22dd4346eb4', name: 'joranchinatravel', service: 'instagram' }
    },
    scheduleOffset: 0 // EST 09:00/15:00
  },
  B: {
    tokenKey: 'NEW_BUFFER_WORKER_URL',
    name: 'Buffer-B',
    channels: {
      pinterest: { id: '6a21bdbec687a22dd45ec2ae', name: 'Joranchinatravel', service: 'pinterest' }
    },
    scheduleOffset: 11 // EST 20:00 (比A晚11小时)
  }
};

// Buffer GraphQL API端点
const BUFFER_API_URL = 'https://api.buffer.com';

// 限流配置
const RATE_LIMIT = {
  GLOBAL_DAILY_MAX: 3,       // 全局单日发布上限（每篇文章1条社媒，每天最多3篇）
  ACCOUNT_QUARTER_MAX: 70,   // 单账户15分钟上限(官方100的70%安全阈值)
  QUOTA_WARNING_THRESHOLD: 0.3 // 配额剩余30%触发预警
};

// 重试配置
const RETRY_CONFIG = {
  MAX_RETRY: 3,
  BASE_DELAY: 2000,
  JITTER: 1000
};

// 图片域名白名单
const ALLOWED_IMAGE_HOST = 'chinaboundtravel.com';
const ALLOWED_IMAGE_PATH = '/img/china-dest/';
const ALLOWED_EXTERNAL_HOSTS = ['image.pollinations.ai', 'images.unsplash.com'];

// ============ 主处理函数 ============

export default {
  async fetch(request, env, ctx) {
    // CORS预检请求处理
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

    const url = new URL(request.url);

    // 健康检查端点
    if (url.pathname === '/health') {
      return jsonResponse({ 
        status: 'ok', 
        service: 'Buffer GraphQL Auto-Poster',
        version: '3.0.0',
        timestamp: new Date().toISOString()
      });
    }

    // 查询渠道端点（调试用）
    if (url.pathname === '/channels') {
      return await handleQueryChannels(env);
    }

    // 主发布端点
    if (url.pathname === '/publish' && request.method === 'POST') {
      return await handlePublish(request, env, ctx);
    }

    // 手动重试队列端点（管理用）
    if (url.pathname === '/retry-queue' && request.method === 'POST') {
      return await processRetryQueue(env);
    }

    // 调试端点：列出排期帖子
  if (url.pathname === '/list-posts') {
    const query = `query GetScheduledPosts($input: PostsInput!) {
      posts(input: $input) {
        edges { node { id text dueAt channel { id name service } } }
      }
    }`;
    const results = {};
    // Buffer-A (FB/IG/Twitter)
    const tokenA = env.BUFFER_WORKER_URL || '';
    try {
      const resp = await fetch(BUFFER_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${tokenA}` },
        body: JSON.stringify({
          query,
          variables: { input: { organizationId: '6a17ddf5e051bed5895272f0', sort: [{ field: 'dueAt', direction: 'asc' }], filter: { status: ['scheduled'] } } }
        })
      });
      results['Buffer-A'] = await resp.json();
    } catch(e) { results['Buffer-A'] = { error: e.message }; }
    // Buffer-B (Pinterest)
    const tokenB = env.NEW_BUFFER_WORKER_URL || '';
    try {
      const resp = await fetch(BUFFER_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${tokenB}` },
        body: JSON.stringify({
          query,
          variables: { input: { organizationId: '6a20329943b37a7289e25b6d', sort: [{ field: 'dueAt', direction: 'asc' }], filter: { status: ['scheduled'] } } }
        })
      });
      results['Buffer-B'] = await resp.json();
    } catch(e) { results['Buffer-B'] = { error: e.message }; }
    return jsonResponse(results);
  }

  // 调试端点：查询 Pinterest boards
  if (url.pathname === '/debug-boards') {
    const token = env.NEW_BUFFER_WORKER_URL || '';
    const queries = [
      { name: 'pinterest_channels', query: 'query { channels(input: { organizationId: "6a20329943b37a7289e25b6d" }) { id name service metadata { ... on PinterestMetadata { boards { id name serviceId url } } } } }' },
      { name: 'all_channels', query: 'query { channels(input: { organizationId: "6a20329943b37a7289e25b6d" }) { id name service } }' }
    ];
    const results = {};
    for (const q of queries) {
      try {
        const resp = await fetch(BUFFER_API_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ query: q.query })
        });
        results[q.name] = await resp.json();
      } catch(e) { results[q.name] = { error: e.message }; }
    }
    return jsonResponse(results);
  }

  // 重置每日计数端点（管理用）
    if (url.pathname === '/reset-daily-count' && request.method === 'POST') {
      const today = new Date().toISOString().split('T')[0];
      const oldCount = await env.KV_STORE.get(`daily_count:${today}`);
      await env.KV_STORE.put(`daily_count:${today}`, '0');
      // 同时重置账户级配额
      for (const accountKey of Object.keys(BUFFER_ACCOUNTS)) {
        await env.KV_STORE.delete(`account_quota:${accountKey}`);
      }
      return jsonResponse({
        success: true,
        message: `Daily count reset: ${oldCount} -> 0 for ${today}`,
        date: today,
        accountQuotasReset: true
      });
    }

    // 查询当前每日计数（调试用）
    if (url.pathname === '/daily-count') {
      const today = new Date().toISOString().split('T')[0];
      const count = await env.KV_STORE.get(`daily_count:${today}`);
      const quotaInfo = {};
      for (const [key, config] of Object.entries(BUFFER_ACCOUNTS)) {
        const quota = await env.KV_STORE.get(`account_quota:${key}`);
        quotaInfo[config.name] = quota || 'no quota record';
      }
      return jsonResponse({
        date: today,
        daily_count: parseInt(count) || 0,
        daily_max: RATE_LIMIT.GLOBAL_DAILY_MAX,
        account_quotas: quotaInfo
      });
    }

    // GA4 周报数据端点（JSON）
  if (url.pathname === '/ga4-report') {
    return await handleGA4Report(env);
  }

  // GA4 周报HTML端点
  if (url.pathname === '/ga4-report-html') {
    return await handleGA4ReportHTML(env);
  }

  // GA4 调试端点（返回原始API响应）
  if (url.pathname === '/ga4-debug') {
    return await handleGA4Debug(env);
  }

  // 404响应
    return jsonResponse({ 
      error: 'Not Found',
      message: 'Available endpoints: /health, /publish, /channels, /retry-queue, /reset-daily-count, /daily-count'
    }, 404);
  },

  /**
   * Cron定时任务处理
   * 触发规则：0 8 * * *（每日EST08:00重发积压任务）
   */
  async scheduled(event, env, ctx) {
    console.log(`[Cron] Triggered at ${new Date(event.scheduledTime).toISOString()}`);
    
    // 每日EST08:00处理重试队列
    await processRetryQueue(env);
    
    return new Response('Cron executed');
  }
};

// ============ 发布处理函数 ============

async function handlePublish(request, env, ctx) {
  try {
    const body = await request.json();
    const { title, desc, cover, url: postUrl } = body;

    // 参数校验
    if (!title || !desc) {
      return jsonResponse({
        success: false,
        error: 'Missing required fields',
        message: 'title and desc are required'
      }, 400);
    }

    // ========== 内容去重检查 ==========
    const contentKey = `${title}::${postUrl || ''}::${body.custom_text ? body.custom_text.slice(0, 60) : 'default'}`;
    const contentHash = await sha256(contentKey);
    const dedupKey = `dedup:${contentHash}`;
    const alreadyPosted = await env.KV_STORE.get(dedupKey);
    if (alreadyPosted) {
      return jsonResponse({
        success: false,
        error: 'Duplicate content',
        message: `相同内容已在 ${alreadyPosted} 发布过，跳过重复。标题: ${title.substring(0, 50)}`
      }, 200);
    }

    // ========== 封面强校验 ==========
    let mediaUrl = cover || '';
    if (mediaUrl) {
      const isValid = validateImageUrl(mediaUrl);
      if (!isValid.valid) {
        return jsonResponse({
          success: false,
          error: 'Image URL blocked',
          message: isValid.message
        }, 400);
      }
      mediaUrl = isValid.url;
    } else {
      return jsonResponse({
        success: false,
        error: 'Missing cover image',
        message: `必须提供 cover 字段，格式: https://${ALLOWED_IMAGE_HOST}${ALLOWED_IMAGE_PATH}分类/图片.jpg`
      }, 400);
    }

    // ========== 全局限流检查 ==========
    const dailyCount = await getDailyPublishCount(env);
    if (dailyCount >= RATE_LIMIT.GLOBAL_DAILY_MAX) {
      // 单日已达上限，仅部署网站，稿件存入重试队列
      await saveToRetryQueue(env, { title, desc, cover, url: postUrl });
      
      return jsonResponse({
        success: false,
        error: 'Daily limit exceeded',
        message: `今日已发布 ${dailyCount} 篇，单日上限 ${RATE_LIMIT.GLOBAL_DAILY_MAX} 篇。稿件已存入队列，明日自动发布。`,
        queued: true
      }, 202);
    }

    // 构建发布内容（优先使用自定义文本）
    const postText = body.custom_text || buildPostText(title, desc, postUrl);

    // 收集所有账户的发布结果
    const allResults = {
      success: [],
      failed: [],
      details: []
    };

    // 遍历双Buffer账户进行发布
    for (const [accountKey, accountConfig] of Object.entries(BUFFER_ACCOUNTS)) {
      // 账户级限流检查
      const accountQuota = await checkAccountQuota(env, accountKey);
      if (!accountQuota.allowed) {
        allResults.failed.push(...Object.keys(accountConfig.channels));
        allResults.details.push({
          platform: accountConfig.name,
          error: `账户限流: ${accountQuota.message}`
        });
        continue;
      }

      // 获取Token
      const token = env[accountConfig.tokenKey];
      if (!token) {
        allResults.failed.push(...Object.keys(accountConfig.channels));
        allResults.details.push({
          platform: accountConfig.name,
          error: 'Token not configured'
        });
        continue;
      }

      // 发布到该账户的渠道
      const results = await publishToBuffer(
        Object.values(accountConfig.channels).map(c => c.id),
        postText,
        mediaUrl,
        token,
        accountConfig.channels,
        env,
        accountKey,
        postUrl
      );

      // 合并结果
      allResults.success.push(...results.success);
      allResults.failed.push(...results.failed);
      allResults.details.push(...results.details);

      // 更新账户限流计数
      await updateAccountQuota(env, accountKey);
    }

    // 更新全局日计数 + 记录去重hash
    if (allResults.success.length > 0) {
      await incrementDailyPublishCount(env);
      await env.KV_STORE.put(dedupKey, new Date().toISOString(), {
        expirationTtl: 30 * 24 * 60 * 60
      });
    }

    // 发送飞书通知
    await sendFeishuNotification(env, {
      title: allResults.success.length > 0 ? '✅ 社媒发布完成' : '⚠️ 社媒发布失败',
      content: `文章: ${title}\n成功: ${allResults.success.join(', ') || '无'}\n失败: ${allResults.failed.join(', ') || '无'}`
    });

    return jsonResponse({
      success: allResults.success.length > 0,
      title,
      platforms: allResults,
      dailyCount: dailyCount + 1
    });

  } catch (error) {
    console.error('[Publish Error]', error);
    return jsonResponse({ success: false, error: error.message }, 500);
  }
}

// ========== 图片URL校验 ==========
function validateImageUrl(url) {
  try {
    const parsed = new URL(url);
    
    // 相对路径转换
    if (url.startsWith('/')) {
      return { valid: true, url: `https://${ALLOWED_IMAGE_HOST}${url}` };
    }

    // 检查是否为允许的外部图片服务
    if (ALLOWED_EXTERNAL_HOSTS.includes(parsed.hostname)) {
      return { valid: true, url };
    }

    // 检查域名
    if (parsed.hostname !== ALLOWED_IMAGE_HOST) {
      return { valid: false, message: `图片域名必须是 ${ALLOWED_IMAGE_HOST} 或允许的外部服务` };
    }

    // 检查路径
    if (!parsed.pathname.startsWith(ALLOWED_IMAGE_PATH)) {
      return { valid: false, message: `图片路径必须以 ${ALLOWED_IMAGE_PATH} 开头` };
    }

    return { valid: true, url };
  } catch {
    return { valid: false, message: '无效的图片URL格式' };
  }
}

// ========== 限流计数函数 ==========
async function getDailyPublishCount(env) {
  const today = new Date().toISOString().split('T')[0];
  const count = await env.KV_STORE.get(`daily_count:${today}`);
  return parseInt(count) || 0;
}

async function incrementDailyPublishCount(env) {
  const today = new Date().toISOString().split('T')[0];
  const count = await getDailyPublishCount(env);
  await env.KV_STORE.put(`daily_count:${today}`, (count + 1).toString());
}

async function checkAccountQuota(env, accountKey) {
  const now = Date.now();
  const windowKey = Math.floor(now / (15 * 60 * 1000)); // 15分钟窗口
  const key = `quota:${accountKey}:${windowKey}`;
  
  const count = await env.KV_STORE.get(key);
  const current = parseInt(count) || 0;

  if (current >= RATE_LIMIT.ACCOUNT_QUARTER_MAX) {
    return { allowed: false, message: `15分钟内已调用 ${current} 次，上限 ${RATE_LIMIT.ACCOUNT_QUARTER_MAX} 次` };
  }

  return { allowed: true, remaining: RATE_LIMIT.ACCOUNT_QUARTER_MAX - current };
}

async function updateAccountQuota(env, accountKey) {
  const now = Date.now();
  const windowKey = Math.floor(now / (15 * 60 * 1000));
  const key = `quota:${accountKey}:${windowKey}`;
  
  const count = await env.KV_STORE.get(key);
  const current = parseInt(count) || 0;
  await env.KV_STORE.put(key, (current + 1).toString());
}

// ========== 重试队列函数 ==========
async function saveToRetryQueue(env, postData) {
  const id = `retry:${Date.now()}:${Math.random().toString(36).substr(2, 9)}`;
  await env.KV_STORE.put(id, JSON.stringify(postData), {
    expirationTtl: 24 * 60 * 60 // 24小时过期
  });
  console.log(`[Queue] Saved to retry queue: ${id}`);
}

async function processRetryQueue(env) {
  console.log('[Queue] Processing retry queue...');
  
  let processed = 0;
  let success = 0;
  let failed = 0;

  // 获取所有重试任务
  const keys = await env.KV_STORE.list({ prefix: 'retry:' });
  
  for (const key of keys.keys) {
    try {
      const data = await env.KV_STORE.get(key);
      if (!data) continue;

      const postData = JSON.parse(data);
      
      // 检查日限额
      const dailyCount = await getDailyPublishCount(env);
      if (dailyCount >= RATE_LIMIT.GLOBAL_DAILY_MAX) {
        console.log('[Queue] Daily limit reached, stopping retry');
        break;
      }

      // 重新发布
      const body = new Request('http://localhost/publish', {
        method: 'POST',
        body: JSON.stringify(postData)
      });
      
      const result = await handlePublish(body, env, null);
      const resultData = await result.json();

      if (resultData.success || resultData.queued) {
        await env.KV_STORE.delete(key);
        success++;
      } else if (resultData.error === 'Duplicate content') {
        // 去重检查命中，直接丢弃
        await env.KV_STORE.delete(key);
        success++;
        console.log('[Queue] Duplicate detected, removed from queue');
      } else {
        // 发布失败但非重复，最多重试一次（已在这里了），删除避免无限循环
        await env.KV_STORE.delete(key);
        failed++;
      }
      
      processed++;
      
      // 每篇间隔（Worker cron模式下次运行间隔足够）
      await new Promise(r => setTimeout(r, 5000));

    } catch (error) {
      console.error('[Queue] Error processing:', error);
      failed++;
    }
  }

  const summary = { processed, success, failed };
  console.log(`[Queue] Retry completed: ${JSON.stringify(summary)}`);

  // 发送通知
  await sendFeishuNotification(env, {
    title: '🔄 重试队列处理完成',
    content: `处理: ${processed}\n成功: ${success}\n失败: ${failed}`
  });

  return jsonResponse(summary);
}

// ========== 发布到Buffer ==========
async function publishToBuffer(channelIds, text, mediaUrl, token, channels, env, accountKey, postUrl) {
  const results = { success: [], failed: [], details: [] };
  const accountConfig = BUFFER_ACCOUNTS[accountKey] || {};

  const mutation = `
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess {
          post { id text dueAt channel { id name service } }
        }
        ... on MutationError { message }
      }
    }
  `;

  for (const channelId of channelIds) {
    const channelInfo = Object.values(channels).find(c => c.id === channelId);
    const service = channelInfo?.service || 'unknown';

    // 计算发布时间：基于账户 scheduleOffset 和平台索引错开发布
    const now = new Date();
    const offsetMs = (accountConfig.scheduleOffset || 0) * 3600000 + (channelIds.indexOf(channelId) + 1) * 7200000;
    const publishTime = new Date(now.getTime() + offsetMs);

    const baseInput = {
      channelId: channelId,
      schedulingType: 'automatic',
      mode: 'customScheduled',
      dueAt: publishTime.toISOString()
    };

    let input = buildPlatformInput(service, text, mediaUrl, baseInput, env, postUrl);
    const variables = { input };

    let attempt = 0;
    let success = false;
    let lastError = null;

    while (attempt < RETRY_CONFIG.MAX_RETRY && !success) {
      try {
        const response = await fetch(BUFFER_API_URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ query: mutation, variables })
        });

        // 检查配额并发送预警
        const remaining = parseInt(response.headers.get('X-RateLimit-Remaining') || '100');
        const limit = parseInt(response.headers.get('X-RateLimit-Limit') || '100');
        if (remaining / limit <= RATE_LIMIT.QUOTA_WARNING_THRESHOLD) {
          await sendFeishuNotification(env, {
            title: '⚠️ Buffer API配额预警',
            content: `账户: ${accountKey}\n平台: ${service}\n剩余配额: ${remaining}/${limit} (${((remaining/limit)*100).toFixed(0)}%)`
          });
        }

        if (!response.ok) {
          const errorText = await response.text();
          
          // 429限流处理
          if (response.status === 429) {
            const retryAfter = parseInt(response.headers.get('Retry-After')) || 60;
            const delay = Math.pow(2, attempt) * RETRY_CONFIG.BASE_DELAY + 
                         Math.random() * RETRY_CONFIG.JITTER;
            
            console.log(`[RateLimit] ${service} - Retry after ${delay}ms (attempt ${attempt+1})`);
            await new Promise(r => setTimeout(r, Math.min(delay, retryAfter * 1000)));
            attempt++;
            continue;
          }
          
          throw new Error(`Buffer API error: ${response.status} - ${errorText}`);
        }

        const data = await response.json();
        
        if (data.errors) {
          throw new Error(data.errors[0].message);
        }

        const result = data.data?.createPost;
        
        if (result?.post) {
          const platform = result.post?.channel?.service || service;
          results.success.push(platform);
          results.details.push({
            platform,
            postId: result.post?.id,
            dueAt: result.post?.dueAt
          });
          success = true;
        } else if (result?.message) {
          throw new Error(result.message);
        }

      } catch (error) {
        lastError = error;
        console.error(`[Buffer Error] ${service}: ${error.message}`);
        
        // Pinterest Board ID 缺失时，自动查询并重试
        if (service === 'pinterest' && error.message.includes('Board ID') && attempt === 0) {
          console.log('[Pinterest] Board ID missing, querying boards...');
          const boardId = await queryPinterestBoardId(token);
          if (boardId) {
            console.log(`[Pinterest] Found board: ${boardId}`);
            env.PINTEREST_BOARD_SERVICE_ID = boardId;
            // 重建 input 带 board ID
            input = buildPlatformInput(service, text, mediaUrl, baseInput, env, postUrl);
            variables.input = input;
            attempt++;
            continue;
          }
        }
        
        // 非429错误，不再重试
        if (!error.message.includes('429') && !error.message.includes('RATE_LIMIT')) {
          break;
        }
        
        attempt++;
        if (attempt < RETRY_CONFIG.MAX_RETRY) {
          const delay = Math.pow(2, attempt) * RETRY_CONFIG.BASE_DELAY;
          await new Promise(r => setTimeout(r, delay));
        }
      }
    }

    if (!success) {
      results.failed.push(service);
      results.details.push({ platform: service, error: lastError?.message || 'Unknown error' });
    }
  }

  return results;
}

// ========== 构建平台特定输入 ==========
function buildPlatformInput(service, text, mediaUrl, baseInput, env, postUrl) {
  let input;

  if (service === 'facebook') {
    const fbText = (text || '').slice(0, 5000);
    input = {
      ...baseInput,
      text: fbText,
      metadata: { facebook: { type: 'post' } },
      assets: mediaUrl ? [{ image: { url: mediaUrl } }] : []
    };
  } else if (service === 'instagram') {
    const cleanText = (text || '').replace(/https?:\/\/[^\s]+/g, '').slice(0, 2200);
    input = {
      ...baseInput,
      text: cleanText,
      metadata: { instagram: { type: 'post', shouldShareToFeed: true } },
      assets: [{ image: { url: mediaUrl } }]
    };
  } else if (service === 'pinterest') {
    const pinTitle = (text || '').slice(0, 100);
    const pinBoardServiceId = env.PINTEREST_BOARD_SERVICE_ID || '719309440424840288';
    const pinLink = postUrl && postUrl.startsWith('http') ? postUrl : 'https://chinaboundtravel.com';
    const pinMeta = {
      title: pinTitle,
      url: pinLink
    };
    if (pinBoardServiceId) pinMeta.boardServiceId = pinBoardServiceId;
    input = {
      ...baseInput,
      text: pinTitle,
      metadata: { pinterest: pinMeta },
      assets: [{ image: { url: mediaUrl } }]
    };
  } else {
    input = {
      ...baseInput,
      text: (text || '').slice(0, 280),
      assets: mediaUrl ? [{ image: { url: mediaUrl } }] : []
    };
  }

  return input;
}

// ========== Pinterest Board 查询 ==========
async function queryPinterestBoardId(token) {
  const query = `
    query {
      account {
        organizations {
          channels(service: "pinterest") {
            id name service
            metadata {
              ... on PinterestMetadata {
                boards { id name serviceId url }
              }
            }
          }
        }
      }
    }
  `;

  try {
    const response = await fetch(BUFFER_API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ query })
    });

    const data = await response.json();
    const orgs = data.data?.account?.organizations || [];
    
    for (const org of orgs) {
      for (const channel of (org.channels || [])) {
        const boards = channel.metadata?.boards || [];
        if (boards.length > 0) {
          // 返回第一个 board 的 serviceId
          return boards[0].serviceId || boards[0].id;
        }
      }
    }
    
    console.log('[Pinterest] No boards found in channel metadata');
    return null;
  } catch (error) {
    console.error('[Pinterest Board Query Error]', error);
    return null;
  }
}

// ========== 辅助函数 ==========

function buildPostText(title, desc, postUrl) {
  const shortDesc = desc.length > 200 ? desc.substring(0, 200) + '...' : desc;
  const hashtags = '#ChinaTravel #ChinaTour #TravelTips';
  const link = postUrl ? `\n\n📖 Read more: ${postUrl}` : '';
  return `${title}\n\n${shortDesc}${link}\n\n${hashtags}`;
}

async function queryChannels(token) {
  const query = `
    query {
      account {
        organizations {
          channels {
            id name service
            metadata {
              ... on PinterestMetadata {
                boards { id name serviceId url }
              }
            }
          }
        }
      }
    }
  `;

  try {
    const response = await fetch(BUFFER_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ query })
    });

    const data = await response.json();
    const channels = [];
    const orgs = data.data?.account?.organizations || [];
    for (const org of orgs) {
      if (org.channels) channels.push(...org.channels);
    }
    
    return channels;
  } catch (error) {
    console.error('[Channel Query Error]', error);
    return [];
  }
}

async function handleQueryChannels(env) {
  const allChannels = {};
  for (const [accountKey, accountConfig] of Object.entries(BUFFER_ACCOUNTS)) {
    const token = env[accountConfig.tokenKey];
    if (!token) {
      allChannels[accountKey] = { success: false, error: 'Token not configured' };
      continue;
    }
    const channels = await queryChannels(token);
    allChannels[accountKey] = { success: true, channels };
  }
  return jsonResponse({ success: true, accounts: allChannels });
}

async function sendFeishuNotification(env, data) {
  if (!env.FEISHU_WEBHOOK_URL) return;
  try {
    await fetch(env.FEISHU_WEBHOOK_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        msg_type: 'post',
        content: {
          post: {
            zh_cn: { title: data.title, content: [[{ tag: 'text', text: data.content }]] }
          }
        }
      })
    });
  } catch (error) {
    console.error('[Feishu Error]', error);
  }
}

async function sha256(text) {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('');
}

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: { 'Content-Type': 'application/json', ...corsHeaders() }
  });
}

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
  };
}

// ============ GA4 Analytics Report ============

async function handleGA4Report(env) {
  const GA4_PROPERTY_ID = env.GA4_PROPERTY_ID || '192133217';
  const GA4_SA_KEY = env.GA4_SERVICE_ACCOUNT_KEY || '';
  const GA_API_URL = `https://analyticsdata.googleapis.com/v1beta/properties/${GA4_PROPERTY_ID}:runReport`;
  const GA_TOKEN_URL = 'https://oauth2.googleapis.com/token';

  // Parse SA key if not already parsed
  let saKey;
  try {
    saKey = typeof GA4_SA_KEY === 'string' ? JSON.parse(GA4_SA_KEY) : GA4_SA_KEY;
  } catch (e) {
    return jsonResponse({ error: 'Invalid GA4 Service Account Key format', detail: e.message }, 500);
  }

  if (!saKey.client_email || !saKey.private_key) {
    return jsonResponse({ error: 'GA4 Service Account Key missing client_email or private_key. Set GA4_SERVICE_ACCOUNT_KEY env variable.' }, 500);
  }

  // Build JWT
  const header = { alg: 'RS256', typ: 'JWT' };
  const now = Math.floor(Date.now() / 1000);
  const payload = {
    iss: saKey.client_email,
    scope: 'https://www.googleapis.com/auth/analytics.readonly',
    aud: GA_TOKEN_URL,
    iat: now,
    exp: now + 3600
  };

  async function base64url(data) {
    const encoded = btoa(typeof data === 'string' ? data : JSON.stringify(data));
    return encoded.replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');
  }

  async function createJWT() {
    const h = await base64url(JSON.stringify(header));
    const p = await base64url(JSON.stringify(payload));
    const message = `${h}.${p}`;

    let keyData = structuredClone(saKey.private_key);
    // Ensure proper PEM format
    if (!keyData.includes('-----BEGIN')) {
      keyData = `-----BEGIN PRIVATE KEY-----\n${keyData}\n-----END PRIVATE KEY-----`;
    }

    const key = await crypto.subtle.importKey(
      'pkcs8',
      pemToArrayBuffer(keyData),
      { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' },
      false,
      ['sign']
    );

    const sig = await crypto.subtle.sign(
      { name: 'RSASSA-PKCS1-v1_5' },
      key,
      new TextEncoder().encode(message)
    );

    const sigB64 = await base64url(String.fromCharCode(...new Uint8Array(sig)));
    return `${message}.${sigB64}`;
  }

  function pemToArrayBuffer(pem) {
    const b64 = pem.replace(/-----BEGIN[^-]+-----/g, '').replace(/-----END[^-]+-----/g, '').replace(/\s/g, '');
    const binary = atob(b64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return bytes.buffer;
  }

  // Get access token
  const jwt = await createJWT();
  const tokenResp = await fetch(GA_TOKEN_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: `grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion=${jwt}`
  });

  if (!tokenResp.ok) {
    const errText = await tokenResp.text();
    return jsonResponse({ error: 'Failed to get GA4 access token', detail: errText }, 500);
  }
  const tokenData = await tokenResp.json();
  const accessToken = tokenData.access_token;

  const gaHeaders = {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  };

  // Date range
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const sevenDaysAgo = new Date(today);
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

  const fmt = (d) => d.toISOString().split('T')[0];
  const dateRange = { startDate: fmt(sevenDaysAgo), endDate: fmt(yesterday) };

  // Run multiple reports in parallel
  const reports = {};

  // 1. Daily metrics
  reports.daily = {
    dateRanges: [dateRange],
    dimensions: [{ name: 'date' }],
    metrics: [
      { name: 'activeUsers' }, { name: 'sessions' }, { name: 'screenPageViews' },
      { name: 'engagedSessions' }, { name: 'bounceRate' }, { name: 'averageSessionDuration' }
    ],
    orderBys: [{ field: 'date', sortOrder: 'ASCENDING' }]
  };

  // 2. Top pages
  reports.topPages = {
    dateRanges: [dateRange],
    dimensions: [{ name: 'pageTitle' }, { name: 'pagePath' }],
    metrics: [
      { name: 'screenPageViews' }, { name: 'sessions' }, { name: 'activeUsers' }, { name: 'averageSessionDuration' }
    ],
    orderBys: [{ field: 'screenPageViews', sortOrder: 'DESCENDING' }],
    limit: 20
  };

  // 3. Traffic sources
  reports.sources = {
    dateRanges: [dateRange],
    dimensions: [{ name: 'sessionDefaultChannelGroup' }],
    metrics: [{ name: 'sessions' }, { name: 'activeUsers' }, { name: 'engagementRate' }],
    orderBys: [{ field: 'sessions', sortOrder: 'DESCENDING' }]
  };

  // 4. Countries
  reports.countries = {
    dateRanges: [dateRange],
    dimensions: [{ name: 'country' }],
    metrics: [{ name: 'activeUsers' }, { name: 'sessions' }, { name: 'screenPageViews' }],
    orderBys: [{ field: 'activeUsers', sortOrder: 'DESCENDING' }],
    limit: 15
  };

  // 5. Devices
  reports.devices = {
    dateRanges: [dateRange],
    dimensions: [{ name: 'deviceCategory' }],
    metrics: [{ name: 'sessions' }, { name: 'activeUsers' }, { name: 'screenPageViews' }],
    orderBys: [{ field: 'sessions', sortOrder: 'DESCENDING' }]
  };

  // 6. New vs Returning
  reports.userType = {
    dateRanges: [dateRange],
    dimensions: [{ name: 'newVsReturning' }],
    metrics: [{ name: 'sessions' }, { name: 'activeUsers' }],
    orderBys: [{ field: 'sessions', sortOrder: 'DESCENDING' }]
  };

  // Execute all reports in parallel
  const results = {};
  for (const [key, body] of Object.entries(reports)) {
    try {
      const resp = await fetch(GA_API_URL, {
        method: 'POST',
        headers: gaHeaders,
        body: JSON.stringify(body)
      });
      if (resp.ok) {
        results[key] = await resp.json();
      } else {
        results[key] = { error: resp.status, text: await resp.text() };
      }
    } catch (e) {
      results[key] = { error: e.message };
    }
  }

  return jsonResponse({
    success: true,
    propertyId: GA4_PROPERTY_ID,
    dateRange,
    reports: results
  });
}

// ============ GA4 HTML Report ============

async function handleGA4ReportHTML(env) {
  // Reuse the JSON report function but parse and render as HTML
  const jsonResp = await handleGA4Report(env);
  const text = await jsonResp.text();
  let data;
  try { data = JSON.parse(text); } catch(e) {
    return new Response('Failed to parse GA4 data', { status: 500, headers: { 'Content-Type': 'text/html' } });
  }

  if (!data.success) {
    return new Response('<h1>Error</h1><p>' + JSON.stringify(data) + '</p>', { status: 500, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
  }

  const r = data.reports;
  const dateRange = data.dateRange;

  // Helper
  function fmtDur(s) {
    s = Number(s) || 0;
    if (s >= 3600) return Math.floor(s/3600) + 'h ' + Math.floor((s%3600)/60) + 'm';
    return Math.floor(s/60) + 'm ' + Math.floor(s%60) + 's';
  }

  // Parse daily
  const daily = (r.daily?.rows || []).map(row => {
    const d = row.dimensionValues[0].value;
    const m = row.metricValues.map(v => v.value);
    return { date: d.slice(0,4)+'-'+d.slice(4,6)+'-'+d.slice(6,8), users: +m[0], sessions: +m[1], pv: +m[2], engaged: +m[3], bounce: +m[4]*100, dur: +m[5] };
  });

  const topPages = (r.topPages?.rows || []).map(row => {
    const dims = row.dimensionValues.map(v => v.value);
    const m = row.metricValues.map(v => v.value);
    return { title: dims[0], path: dims[1], views: +m[0], sessions: +m[1], users: +m[2], dur: +m[3] };
  });

  const chNames = { 'Organic Search':'自然搜索', 'Direct':'直接访问', 'Social':'社交媒体', 'Referral':'外部引荐', 'Paid Search':'付费搜索', 'Email':'邮件营销', '(Other)':'其他' };
  const sources = (r.sources?.rows || []).map(row => {
    const ch = row.dimensionValues[0].value;
    const m = row.metricValues.map(v => v.value);
    return { channel: ch, sessions: +m[0], users: +m[1], eng: +m[2]*100 };
  });

  const countries = (r.countries?.rows || []).map(row => {
    const c = row.dimensionValues[0].value;
    const m = row.metricValues.map(v => v.value);
    return { country: c, users: +m[0], sessions: +m[1], pv: +m[2] };
  });

  const devNames = { desktop:'桌面端', mobile:'移动端', tablet:'平板' };
  const devices = (r.devices?.rows || []).map(row => {
    const dev = row.dimensionValues[0].value;
    const m = row.metricValues.map(v => v.value);
    return { device: dev, sessions: +m[0], users: +m[1], pv: +m[2] };
  });

  const userType = (r.userType?.rows || []).map(row => {
    const t = row.dimensionValues[0].value;
    const m = row.metricValues.map(v => v.value);
    return { type: t, sessions: +m[0], users: +m[1] };
  });

  // Totals
  const tU = daily.reduce((s,d)=>s+d.users,0);
  const tS = daily.reduce((s,d)=>s+d.sessions,0);
  const tP = daily.reduce((s,d)=>s+d.pv,0);
  const tE = daily.reduce((s,d)=>s+d.engaged,0);
  const aB = daily.length ? daily.reduce((s,d)=>s+d.bounce,0)/daily.length : 0;
  const aD = daily.length ? daily.reduce((s,d)=>s+d.dur,0)/daily.length : 0;

  const today = new Date().toISOString().split('T')[0];

  let h = `<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><title>GA4 周报 - ChinaBoundTravel</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f7fa;color:#1a1a2e;padding:20px}
.container{max-width:960px;margin:0 auto}
h1{font-size:24px;margin-bottom:4px}
h2{font-size:18px;margin:24px 0 12px;padding-bottom:8px;border-bottom:2px solid #e8ecf1}
.meta{color:#666;font-size:13px;margin-bottom:20px}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:24px}
.card{background:#fff;border-radius:10px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,0.08)}
.card .label{font-size:12px;color:#888;text-transform:uppercase;letter-spacing:0.5px}
.card .value{font-size:28px;font-weight:700;margin-top:4px}
table{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.08);margin-bottom:20px}
th{background:#f8f9fb;font-size:12px;text-align:left;padding:10px 12px;color:#666;font-weight:600;text-transform:uppercase;letter-spacing:0.3px}
td{padding:10px 12px;font-size:14px;border-top:1px solid #f0f2f5}
tr:hover td{background:#fafbfc}
.tag{display:inline-block;background:#e8f4fd;color:#0288d1;padding:2px 8px;border-radius:4px;font-size:12px}
.insights{background:#fff;border-radius:10px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,0.08)}
.insights li{margin:8px 0;font-size:14px;line-height:1.6}
.trend{font-size:14px;padding:12px 16px;background:#fff;border-radius:10px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,0.08)}
</style></head><body>
<div class="container">
<h1>ChinaBoundTravel - 周度数据分析报告</h1>
<p class="meta">报告生成时间：${today} | 数据周期：${dateRange.startDate} ~ ${dateRange.endDate}</p>

<h2>核心指标概览</h2>
<div class="cards">
<div class="card"><div class="label">活跃用户</div><div class="value">${tU.toLocaleString()}</div></div>
<div class="card"><div class="label">会话总数</div><div class="value">${tS.toLocaleString()}</div></div>
<div class="card"><div class="label">页面浏览量</div><div class="value">${tP.toLocaleString()}</div></div>
<div class="card"><div class="label">互动会话</div><div class="value">${tE.toLocaleString()}</div></div>
<div class="card"><div class="label">平均跳出率</div><div class="value">${aB.toFixed(1)}%</div></div>
<div class="card"><div class="label">平均会话时长</div><div class="value">${fmtDur(aD)}</div></div>
</div>`;

  // Daily trend
  if (daily.length >= 2) {
    const half = Math.floor(daily.length/2);
    const fH = daily.slice(0,half).reduce((s,d)=>s+d.users,0);
    const sH = daily.slice(half).reduce((s,d)=>s+d.users,0);
    const trend = sH > fH ? '📈 上升' : sH < fH ? '📉 下降' : '➡️ 持平';
    h += `<div class="trend">趋势：${trend}（前半周 ${fH} 访客 → 后半周 ${sH} 访客）</div>`;
  }

  h += `<h2>每日趋势</h2><table><tr><th>日期</th><th>访客数</th><th>会话数</th><th>浏览量</th><th>互动会话</th><th>跳出率</th><th>平均时长</th></tr>`;
  for (const d of daily) {
    h += `<tr><td>${d.date}</td><td>${d.users}</td><td>${d.sessions}</td><td>${d.pv}</td><td>${d.engaged}</td><td>${d.bounce.toFixed(1)}%</td><td>${fmtDur(d.dur)}</td></tr>`;
  }
  h += `</table>`;

  // Top pages
  h += `<h2>热门页面 Top 10</h2><table><tr><th>#</th><th>页面标题</th><th>路径</th><th>浏览量</th><th>会话数</th><th>访客数</th><th>平均时长</th></tr>`;
  for (let i = 0; i < Math.min(topPages.length, 10); i++) {
    const p = topPages[i];
    h += `<tr><td>${i+1}</td><td>${p.title.slice(0,50)}</td><td><span class="tag">${p.path}</span></td><td>${p.views}</td><td>${p.sessions}</td><td>${p.users}</td><td>${fmtDur(p.dur)}</td></tr>`;
  }
  h += `</table>`;

  // Sources
  h += `<h2>流量来源渠道</h2><table><tr><th>渠道</th><th>会话数</th><th>访客数</th><th>互动率</th></tr>`;
  for (const s of sources) {
    h += `<tr><td>${chNames[s.channel]||s.channel} (${s.channel})</td><td>${s.sessions}</td><td>${s.users}</td><td>${s.eng.toFixed(1)}%</td></tr>`;
  }
  h += `</table>`;

  // Countries
  h += `<h2>访客地区分布</h2><table><tr><th>国家/地区</th><th>访客数</th><th>会话数</th><th>浏览量</th></tr>`;
  for (let i = 0; i < Math.min(countries.length, 10); i++) {
    const c = countries[i];
    h += `<tr><td>${c.country}</td><td>${c.users}</td><td>${c.sessions}</td><td>${c.pv}</td></tr>`;
  }
  h += `</table>`;

  // Devices
  h += `<h2>设备分布</h2><table><tr><th>设备类型</th><th>会话数</th><th>访客数</th><th>浏览量</th></tr>`;
  for (const d of devices) {
    h += `<tr><td>${devNames[d.device.toLowerCase()]||d.device}</td><td>${d.sessions}</td><td>${d.users}</td><td>${d.pv}</td></tr>`;
  }
  h += `</table>`;

  // User type
  h += `<h2>新老访客比例</h2><table><tr><th>类型</th><th>会话数</th><th>访客数</th></tr>`;
  for (const u of userType) {
    const cn = u.type==='new'?'新访客':u.type==='returning'?'回访访客':u.type;
    h += `<tr><td>${cn}</td><td>${u.sessions}</td><td>${u.users}</td></tr>`;
  }
  h += `</table>`;

  // Insights
  h += `<h2>洞察与建议</h2><div class="insights"><ul>`;
  if (topPages.length > 0) h += `<li><strong>最受欢迎页面</strong>: "${topPages[0].title.slice(0,50)}"（${topPages[0].views} 次浏览）</li>`;
  if (sources.length > 0) h += `<li><strong>最大流量渠道</strong>: ${chNames[sources[0].channel]||sources[0].channel}（${sources[0].sessions} 个会话）</li>`;
  const nw = userType.find(u=>u.type==='new');
  if (nw && tU > 0) {
    const pct = (nw.users/tU*100).toFixed(1);
    h += `<li><strong>新访客占比</strong>: ${pct}%</li>`;
  }
  if (aB > 70) h += `<li>⚠️ 跳出率偏高 (${aB.toFixed(1)}%) — 建议优化落地页</li>`;
  else if (aB > 0 && aB < 40) h += `<li>✅ 跳出率健康 (${aB.toFixed(1)}%)</li>`;
  h += `</ul></div>`;

  h += `<p style="text-align:center;color:#999;font-size:12px;margin-top:30px">数据来源：Google Analytics 4 | 由 GA4 Analytics Data API 自动生成</p></div></body></html>`;

  return new Response(h, {
    headers: { 'Content-Type': 'text/html; charset=utf-8', 'Access-Control-Allow-Origin': '*' }
  });
}

// ============ GA4 Debug ============

async function handleGA4Debug(env) {
  const GA4_PROPERTY_ID = env.GA4_PROPERTY_ID || '192133217';
  const GA4_SA_KEY = env.GA4_SERVICE_ACCOUNT_KEY || '';
  const GA_TOKEN_URL = 'https://oauth2.googleapis.com/token';
  const GA_API_URL = `https://analyticsdata.googleapis.com/v1beta/properties/${GA4_PROPERTY_ID}:runReport`;

  // Check if key exists
  const debug = { hasKey: !!GA4_SA_KEY, keyLength: GA4_SA_KEY.length, propertyId: GA4_PROPERTY_ID };

  if (!GA4_SA_KEY) {
    return jsonResponse({ ...debug, error: 'GA4_SERVICE_ACCOUNT_KEY not set' });
  }

  let saKey;
  try { saKey = JSON.parse(GA4_SA_KEY); } catch(e) { return jsonResponse({ ...debug, error: 'Invalid JSON key', parseError: e.message }); }

  // Build JWT
  async function base64url(data) {
    const encoded = btoa(typeof data === 'string' ? data : JSON.stringify(data));
    return encoded.replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');
  }

  const header = { alg: 'RS256', typ: 'JWT' };
  const now = Math.floor(Date.now() / 1000);
  const payload = { iss: saKey.client_email, scope: 'https://www.googleapis.com/auth/analytics.readonly', aud: GA_TOKEN_URL, iat: now, exp: now + 3600 };

  try {
    const h = await base64url(JSON.stringify(header));
    const p = await base64url(JSON.stringify(payload));
    const message = `${h}.${p}`;

    const keyData = saKey.private_key;
    const key = await crypto.subtle.importKey('pkcs8', pemToArrayBuffer(keyData), { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['sign']);
    const sig = await crypto.subtle.sign({ name: 'RSASSA-PKCS1-v1_5' }, key, new TextEncoder().encode(message));
    const sigB64 = await base64url(String.fromCharCode(...new Uint8Array(sig)));
    const jwt = `${message}.${sigB64}`;

    // Get token
    const tokenResp = await fetch(GA_TOKEN_URL, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: `grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion=${jwt}` });
    const tokenData = await tokenResp.json();
    debug.tokenStatus = tokenResp.status;
    debug.tokenError = tokenData.error || null;

    if (!tokenResp.ok) {
      return jsonResponse({ ...debug, error: 'Token request failed' });
    }

    const accessToken = tokenData.access_token;
    debug.tokenLength = accessToken.length;

    // Simple test query
    const testResp = await fetch(GA_API_URL, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ dateRanges: [{ startDate: '2026-06-23', endDate: '2026-06-29' }], dimensions: [{ name: 'date' }], metrics: [{ name: 'activeUsers' }] })
    });
    const testData = await testResp.json();
    debug.apiStatus = testResp.status;
    debug.apiResponse = testData;

    return jsonResponse(debug);
  } catch(e) {
    return jsonResponse({ ...debug, error: e.message, stack: e.stack });
  }
}