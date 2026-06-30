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
  GLOBAL_DAILY_MAX: 5,       // 全局单日发布上限（支持多篇不同内容/配图的帖子）
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

    // 404响应
    return jsonResponse({ 
      error: 'Not Found',
      message: 'Available endpoints: /health, /publish, /channels, /retry-queue'
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

    // 更新全局日计数
    if (allResults.success.length > 0) {
      await incrementDailyPublishCount(env);
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

      if (resultData.success) {
        await env.KV_STORE.delete(key);
        success++;
      } else {
        failed++;
      }
      
      processed++;
      
      // 每篇间隔至少90分钟
      await new Promise(r => setTimeout(r, 1000));

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

    const baseInput = {
      channelId: channelId,
      schedulingType: 'automatic',
      mode: 'addToQueue'
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
    const pinText = (text || '').slice(0, 500);
    const pinBoardServiceId = env.PINTEREST_BOARD_SERVICE_ID || '';
    const pinMeta = {
      title: pinTitle,
      url: postUrl || 'https://chinaboundtravel.com',
      description: pinText
    };
    if (pinBoardServiceId) pinMeta.boardServiceId = pinBoardServiceId;
    input = {
      ...baseInput,
      text: pinText,
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

// ============ 辅助函数 ============

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