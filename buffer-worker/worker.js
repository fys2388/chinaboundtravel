/**
 * Cloudflare Worker - Buffer GraphQL API Auto-Poster
 * 
 * 功能：
 * 1. 接收GitHub Action推送的博文数据
 * 2. 调用Buffer GraphQL API发布到FB/Instagram/X
 * 3. 预留Cron定时任务：每30分钟拉取评论+AI回复
 * 
 * @author Joran - ChinaBoundTravel
 * @version 2.0.0
 */

// ============ 配置常量 ============

/**
 * 多Buffer账户配置
 * 账户1：主账户 - 绑定Twitter/X、Facebook、Instagram
 * 账户2：Pinterest专用账户
 */
const BUFFER_ACCOUNTS = {
  main: {
    token: 'BUFFER_TOKEN',
    channels: {
      x: {
        id: '6a202882c687a22dd45735b6',
        name: 'fys2388',
        service: 'twitter'
      },
      facebook: {
        id: '6a17e0c4c687a22dd4346d3c',
        name: 'ChinaBound Travel',
        service: 'facebook'
      },
      instagram: {
        id: '6a17e14dc687a22dd4346eb4',
        name: 'joranchinatravel',
        service: 'instagram'
      }
    }
  },
  pinterest: {
    token: 'BUFFER_TOKEN_PINTEREST',
    channels: {
      pinterest: {
        id: '6a21bdbec687a22dd45ec2ae',
        name: 'Joranchinatravel',
        service: 'pinterest'
      }
    }
  }
};

// Buffer GraphQL API端点
const BUFFER_API_URL = 'https://api.buffer.com';

// 目标发布平台
const TARGET_PLATFORMS = ['x', 'facebook', 'instagram', 'pinterest'];

// ============ 主处理函数 ============

export default {
  /**
   * HTTP请求处理
   * @param {Request} request - 入站请求
   * @param {Env} env - 环境变量
   * @param {ExecutionContext} ctx - 执行上下文
   */
  async fetch(request, env, ctx) {
    // CORS预检请求处理
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: corsHeaders()
      });
    }

    // 路由分发
    const url = new URL(request.url);
    
    // 健康检查端点
    if (url.pathname === '/health') {
      return jsonResponse({ 
        status: 'ok', 
        service: 'Buffer GraphQL Auto-Poster',
        version: '2.0.0',
        timestamp: new Date().toISOString()
      });
    }

    // 查询渠道端点（调试用）
    if (url.pathname === '/channels') {
      return await handleQueryChannels(env);
    }

    // 主发布端点
    if (url.pathname === '/publish' && request.method === 'POST') {
      return await handlePublish(request, env);
    }

    // 评论处理端点（预留）
    if (url.pathname === '/comments') {
      return await handleComments(env);
    }

    // 404响应
    return jsonResponse({ 
      error: 'Not Found',
      message: 'Available endpoints: /health, /publish, /channels, /comments'
    }, 404);
  },

  /**
   * Cron定时任务处理
   * 触发规则：* /30 * * * *（每30分钟）
   * 
   * @param {ScheduledEvent} event - 定时事件
   * @param {Env} env - 环境变量
   * @param {ExecutionContext} ctx - 执行上下文
   */
  async scheduled(event, env, ctx) {
    console.log(`[Cron] Triggered at ${new Date(event.scheduledTime).toISOString()}`);
    
    // TODO: 评论抓取+AI回复逻辑
    // 1. 调用Buffer API获取各平台最新评论
    // 2. 过滤未回复评论
    // 3. 调用DeepSeek AI生成Joran人设回复
    // 4. 自动发布回复
    
    const result = await processComments(env);
    
    // 发送执行结果通知
    if (env.FEISHU_WEBHOOK_URL) {
      await sendFeishuNotification(env.FEISHU_WEBHOOK_URL, {
        title: '🔄 Buffer评论处理完成',
        content: `处理时间: ${new Date().toISOString()}\n结果: ${JSON.stringify(result)}`
      });
    }
    
    return new Response('Cron executed');
  }
};

// ============ 发布处理函数 ============

/**
 * 处理发布请求
 * @param {Request} request - 入站请求
 * @param {Env} env - 环境变量
 */
async function handlePublish(request, env) {
  try {
    // 解析请求体
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

    // ========== 图文错配防火墙：强制校验图片域名 ==========
    // 规则：cover 必须是本站 CDN 图片 (chinaboundtravel.com/img/china-dest/)
    // 禁止 picsum.photos/unsplash 等随机外链图
    let mediaUrl = cover || '';
    if (mediaUrl) {
      const isOurDomain = mediaUrl.includes('chinaboundtravel.com') && 
                          mediaUrl.includes('/img/china-dest/');
      const isRelativePath = mediaUrl.startsWith('/img/china-dest/');
      
      if (!isOurDomain && !isRelativePath) {
        // 外链图直接拦截
        return jsonResponse({
          success: false,
          error: 'Image URL blocked',
          message: 'cover 必须使用本站图片: https://chinaboundtravel.com/img/china-dest/xxx.jpg，禁止 picsum.photos/unsplash 等随机外链图'
        }, 400);
      }

      // 相对路径转完整 URL
      if (isRelativePath) {
        mediaUrl = 'https://chinaboundtravel.com' + mediaUrl;
      }
    } else {
      // 没有 cover 则直接拒绝发布（社媒必须配图）
      return jsonResponse({
        success: false,
        error: 'Missing cover image',
        message: '必须提供 cover 字段，格式: https://chinaboundtravel.com/img/china-dest/分类/图片.jpg'
      }, 400);
    }

    // 构建发布内容
    const postText = buildPostText(title, desc, postUrl);

    // 收集所有账户的发布结果
    const allResults = {
      success: [],
      failed: [],
      details: []
    };

    // 遍历所有Buffer账户进行发布
    for (const [accountName, accountConfig] of Object.entries(BUFFER_ACCOUNTS)) {
      // 获取该账户的Token
      const token = env[accountConfig.token];
      if (!token) {
        console.warn(`[Publish] Token not found for account: ${accountName}`);
        continue;
      }

      // 获取该账户的目标渠道ID
      const channelIds = getChannelIdsByAccount(accountName);
      if (channelIds.length === 0) {
        console.warn(`[Publish] No channels configured for account: ${accountName}`);
        continue;
      }

      // 发布到该账户的渠道
      const results = await publishToBuffer(channelIds, postText, mediaUrl, token, accountConfig.channels, env);
      
      // 合并结果
      allResults.success.push(...results.success);
      allResults.failed.push(...results.failed);
      allResults.details.push(...results.details);
    }

    // 发送飞书通知
    if (env.FEISHU_WEBHOOK_URL) {
      await sendFeishuNotification(env.FEISHU_WEBHOOK_URL, {
        title: '✅ 社媒发布完成',
        content: `文章: ${title}\n成功: ${allResults.success.join(', ') || '无'}\n失败: ${allResults.failed.join(', ') || '无'}`
      });
    }

    return jsonResponse({
      success: allResults.success.length > 0,
      title,
      platforms: allResults
    });

  } catch (error) {
    console.error('[Publish Error]', error);
    
    return jsonResponse({
      success: false,
      error: error.message,
      stack: error.stack
    }, 500);
  }
}

/**
 * 构建发布文本
 * @param {string} title - 文章标题
 * @param {string} desc - 文章描述
 * @param {string} postUrl - 文章URL
 */
function buildPostText(title, desc, postUrl) {
  // 截取描述前200字符
  const shortDesc = desc.length > 200 ? desc.substring(0, 200) + '...' : desc;
  
  // 添加话题标签
  const hashtags = '#ChinaTravel #ChinaTour #TravelTips';
  
  // 添加原文链接
  const link = postUrl ? `\n\n📖 Read more: ${postUrl}` : '';
  
  return `${title}\n\n${shortDesc}${link}\n\n${hashtags}`;
}

/**
 * 获取指定账户的目标渠道ID列表
 * @param {string} accountName - 账户名称
 */
function getChannelIdsByAccount(accountName) {
  const ids = [];
  const accountConfig = BUFFER_ACCOUNTS[accountName];
  
  if (!accountConfig) {
    return ids;
  }

  // 获取该账户的所有渠道
  for (const [platform, channel] of Object.entries(accountConfig.channels)) {
    // 检查是否在目标平台列表中
    if (TARGET_PLATFORMS.includes(platform) && channel.id && channel.id.trim()) {
      ids.push(channel.id);
    }
  }
  
  return ids;
}

/**
 * 发布到Buffer
 * @param {string[]} channelIds - 渠道ID列表
 * @param {string} text - 发布文本
 * @param {string} mediaUrl - 媒体URL
 * @param {string} token - Buffer Token
 * @param {object} channels - 渠道配置信息
 */
async function publishToBuffer(channelIds, text, mediaUrl, token, channels, env) {
  const results = {
    success: [],
    failed: [],
    details: []
  };

  // GraphQL Mutation - 使用Buffer官方API正确格式
  const mutation = `
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess {
          post {
            id
            text
            dueAt
            channel {
              id
              name
              service
            }
          }
        }
        ... on MutationError {
          message
        }
      }
    }
  `;

  // 为每个渠道单独发布 — 分平台差异化配置
  for (const channelId of channelIds) {
    const channelInfo = Object.values(channels).find(c => c.id === channelId);
    const service = channelInfo?.service || 'unknown';

    // 公共字段
    const baseInput = {
      channelId: channelId,
      schedulingType: 'automatic',
      mode: 'addToQueue'
    };

    let input;

    if (service === 'facebook') {
      // Facebook: text + metadata.facebook.type: post + 可选配图
      // 文案截断 5000 字符，文末追加官网链接
      const fbText = (text || '').slice(0, 5000);
      input = {
        ...baseInput,
        text: fbText,
        metadata: {
          facebook: {
            type: 'post'
          }
        },
        assets: mediaUrl ? [{ image: { url: mediaUrl } }] : []
      };
    } else if (service === 'instagram') {
      // Instagram: type: post + shouldShareToFeed: true + 强制配图 + 文案≤2200且不可放外链
      const cleanText = (text || '').replace(/https?:\/\/[^\s]+/g, '').slice(0, 2200);
      input = {
        ...baseInput,
        text: cleanText,
        metadata: {
          instagram: {
            type: 'post',
            shouldShareToFeed: true
          }
        },
        assets: [{ image: { url: mediaUrl } }]
      };
    } else if (service === 'pinterest') {
      // Pinterest: text + metadata.pinterest.title + url + boardServiceId + 竖图
      // 在 Buffer 后台配置 boards，把 serviceId 设为 PINTEREST_BOARD_SERVICE_ID 环境变量
      const pinTitle = (text || '').slice(0, 100);
      const pinText = (text || '').slice(0, 500);
      const pinBoardServiceId = env.PINTEREST_BOARD_SERVICE_ID || '';
      const pinMeta = { title: pinTitle, url: 'https://chinaboundtravel.com' };
      if (pinBoardServiceId) pinMeta.boardServiceId = pinBoardServiceId;
      input = {
        ...baseInput,
        text: pinText,
        metadata: { pinterest: pinMeta },
        assets: [{ image: { url: mediaUrl } }]
      };
    } else {
      // Twitter / X 等其他平台：沿用 text + 可选配图
      input = {
        ...baseInput,
        text: (text || '').slice(0, 280),
        assets: mediaUrl ? [{ image: { url: mediaUrl } }] : []
      };
    }

    const variables = { input };

    try {
      const response = await fetch(BUFFER_API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          query: mutation,
          variables: variables
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Buffer API error: ${response.status} - ${errorText}`);
      }

      const data = await response.json();
      
      if (data.errors) {
        throw new Error(data.errors[0].message);
      }

      const result = data.data?.createPost;
      
      if (result?.post) {
        const platform = result.post?.channel?.service || 'unknown';
        results.success.push(platform);
        results.details.push({
          platform,
          postId: result.post?.id,
          dueAt: result.post?.dueAt
        });
      } else if (result?.message) {
        results.failed.push(service);
        results.details.push({
          platform: service,
          error: result.message
        });
      }

    } catch (error) {
      console.error('[Buffer API Error]', error);
      results.failed.push(service);
      results.details.push({
        platform: service,
        error: error.message
      });
    }
  }

  return results;
}

// ============ 渠道查询函数 ============

/**
 * 查询Buffer渠道（调试用）
 * @param {string} token - Buffer Token
 */
async function queryChannels(token) {
  const query = `
    query {
      account {
        organizations {
          channels {
            id
            name
            service
            metadata {
              ... on PinterestMetadata {
                boards {
                  id
                  name
                  serviceId
                  url
                }
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
    
    // 提取所有组织的渠道
    const channels = [];
    const orgs = data.data?.account?.organizations || [];
    for (const org of orgs) {
      if (org.channels) {
        channels.push(...org.channels);
      }
    }
    
    return channels;

  } catch (error) {
    console.error('[Channel Query Error]', error);
    return [];
  }
}

/**
 * 处理渠道查询请求
 * @param {Env} env - 环境变量
 */
async function handleQueryChannels(env) {
  const allChannels = {};

  // 遍历所有Buffer账户查询渠道
  for (const [accountName, accountConfig] of Object.entries(BUFFER_ACCOUNTS)) {
    const token = env[accountConfig.token];
    if (!token) {
      allChannels[accountName] = {
        success: false,
        error: 'Token not configured'
      };
      continue;
    }

    const channels = await queryChannels(token);
    allChannels[accountName] = {
      success: true,
      channels: channels
    };
  }

  return jsonResponse({
    success: true,
    accounts: allChannels
  });
}

// ============ 评论处理函数（预留） ============

/**
 * 处理评论（Cron任务调用）
 * @param {Env} env - 环境变量
 */
async function processComments(env) {
  // TODO: 实现评论抓取和AI回复逻辑
  // 
  // 步骤：
  // 1. 调用Buffer API获取各平台最新评论
  //    query { updates(first: 50) { edges { node { id comments { text author } } } } }
  // 
  // 2. 过滤未回复的评论
  // 
  // 3. 调用DeepSeek AI生成回复
  //    - 使用Joran人设：加州美国人，定居成都10年
  //    - 回复风格：友好、实用、真实
  // 
  // 4. 发布回复
  //    mutation CreateComment($updateId: ID!, $text: String!) { ... }
  
  console.log('[Comments] Processing scheduled comment task...');
  
  return {
    processed: 0,
    replied: 0,
    message: 'Comment processing not yet implemented'
  };
}

/**
 * 评论处理端点
 * @param {Env} env - 环境变量
 */
async function handleComments(env) {
  const result = await processComments(env);
  return jsonResponse(result);
}

// ============ 飞书通知函数 ============

/**
 * 发送飞书通知
 * @param {string} webhookUrl - 飞书Webhook URL
 * @param {object} data - 通知数据
 */
async function sendFeishuNotification(webhookUrl, data) {
  try {
    await fetch(webhookUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        msg_type: 'post',
        content: {
          post: {
            zh_cn: {
              title: data.title,
              content: [[{ tag: 'text', text: data.content }]]
            }
          }
        }
      })
    });
  } catch (error) {
    console.error('[Feishu Error]', error);
  }
}

// ============ 工具函数 ============

/**
 * JSON响应辅助函数
 * @param {object} data - 响应数据
 * @param {number} status - HTTP状态码
 */
function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...corsHeaders()
    }
  });
}

/**
 * CORS头部
 */
function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
  };
}