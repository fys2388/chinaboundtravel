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
 * 各社交平台Channel ID映射
 * 
 * 如何获取Channel ID：
 * 1. 登录Buffer后台 → Settings → API
 * 2. 使用查询语句获取所有渠道：
 *    query { organization { channels { id, name, service } } }
 * 3. 将返回的id填入下方对应平台
 */
const CHANNEL_MAP = {
  facebook: {
    id: 'REPLACE_WITH_FACEBOOK_CHANNEL_ID',  // 例如: '5f8a9b7c1234567890abcdef'
    name: 'ChinaBoundTravel Facebook Page'
  },
  instagram: {
    id: 'REPLACE_WITH_INSTAGRAM_CHANNEL_ID',  // 例如: '5f8a9b7c1234567890abcdeg'
    name: 'ChinaBoundTravel Instagram'
  },
  x: {
    id: 'REPLACE_WITH_X_CHANNEL_ID',  // 例如: '5f8a9b7c1234567890abcdeh'
    name: 'ChinaBoundTravel X (Twitter)'
  }
};

// Buffer GraphQL API端点
const BUFFER_API_URL = 'https://api.bufferapp.com/graphql';

// 目标发布平台
const TARGET_PLATFORMS = ['facebook', 'instagram', 'x'];

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
      return await queryChannels(env.BUFFER_TOKEN);
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
   * 触发规则：*/30 * * * *（每30分钟）
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

    // 构建发布内容
    const postText = buildPostText(title, desc, postUrl);
    const mediaUrl = cover || '';

    // 获取目标渠道ID
    const channelIds = getChannelIds();
    
    if (channelIds.length === 0) {
      return jsonResponse({
        success: false,
        error: 'No channels configured',
        message: 'Please configure CHANNEL_MAP with valid channel IDs'
      }, 400);
    }

    // 调用Buffer GraphQL API发布
    const results = await publishToBuffer(channelIds, postText, mediaUrl, env.BUFFER_TOKEN);

    // 发送飞书通知
    if (env.FEISHU_WEBHOOK_URL) {
      await sendFeishuNotification(env.FEISHU_WEBHOOK_URL, {
        title: '✅ 社媒发布完成',
        content: `文章: ${title}\n平台: ${results.success.join(', ')}\n失败: ${results.failed.join(', ') || '无'}`
      });
    }

    return jsonResponse({
      success: true,
      title,
      platforms: results
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
 * 获取目标渠道ID列表
 */
function getChannelIds() {
  const ids = [];
  
  for (const platform of TARGET_PLATFORMS) {
    const channel = CHANNEL_MAP[platform];
    if (channel && channel.id && !channel.id.startsWith('REPLACE_')) {
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
 */
async function publishToBuffer(channelIds, text, mediaUrl, token) {
  const results = {
    success: [],
    failed: [],
    details: []
  };

  // GraphQL Mutation
  const mutation = `
    mutation CreatePost($channels: [ID!]!, $text: String!, $mediaUrl: String) {
      createUpdate(input: {
        channelIds: $channels,
        text: $text,
        media: { link: $mediaUrl },
        scheduling: { scheduleType: QUEUE }
      }) {
        updates {
          id
          status
          channel {
            name
            service
          }
        }
      }
    }
  `;

  const variables = {
    channels: channelIds,
    text: text,
    mediaUrl: mediaUrl || null
  };

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
      throw new Error(`Buffer API error: ${response.status}`);
    }

    const data = await response.json();
    
    if (data.errors) {
      throw new Error(data.errors[0].message);
    }

    const updates = data.data?.createUpdate?.updates || [];
    
    for (const update of updates) {
      const platform = update.channel?.service || 'unknown';
      if (update.id) {
        results.success.push(platform);
        results.details.push({
          platform,
          updateId: update.id,
          status: update.status
        });
      } else {
        results.failed.push(platform);
      }
    }

  } catch (error) {
    console.error('[Buffer API Error]', error);
    results.failed.push('all');
    results.error = error.message;
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
      organization {
        channels {
          id
          name
          service
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
    
    return jsonResponse({
      success: true,
      channels: data.data?.organization?.channels || []
    });

  } catch (error) {
    return jsonResponse({
      success: false,
      error: error.message
    }, 500);
  }
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