/**
 * Buffer GraphQL 客户端 - 支持双账号配置 + 代理
 * Account A: Pinterest, YouTube, TikTok
 * Account B: Facebook, Instagram, Twitter
 */

const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');

class BufferClient {
  constructor(configPath) {
    this.config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
    this.baseUrl = this.config.api.base_url;
    this.accounts = this.config.accounts;
    this.platformAccountMap = this.config.platform_account_map;
    this.timezone = this.config.default_schedule.timezone;
    this.bestTimes = this.config.default_schedule.best_times;
    this.proxyUrl = this.detectProxy();
  }

  /**
   * 检测代理配置
   */
  detectProxy() {
    // 优先级: 环境变量 > 配置文件 > 无代理
    const envProxy = process.env.HTTPS_PROXY || process.env.HTTP_PROXY;
    if (envProxy) {
      console.log('🔌 使用环境变量代理:', envProxy);
      return envProxy;
    }
    
    // 检查配置文件中的代理
    if (this.config.proxy && this.config.proxy.enabled) {
      console.log('🔌 使用配置文件代理:', this.config.proxy.url);
      return this.config.proxy.url;
    }
    
    return null;
  }

  /**
   * 测试代理是否可用
   */
  async testProxy(proxyUrl) {
    if (!proxyUrl) return false;
    
    return new Promise((resolve) => {
      const url = new URL(proxyUrl);
      const options = {
        hostname: url.hostname,
        port: url.port || (url.protocol === 'https:' ? 443 : 80),
        path: '/',
        method: 'CONNECT',
        timeout: 5000
      };
      
      const req = http.request(options);
      req.on('connect', (res, socket) => {
        socket.destroy();
        resolve(res.statusCode === 200);
      });
      req.on('error', () => resolve(false));
      req.on('timeout', () => { req.destroy(); resolve(false); });
      req.end();
    });
  }

  /**
   * 根据平台获取对应的账号配置
   */
  getAccountForPlatform(platform) {
    const accountKey = this.platformAccountMap[platform];
    if (!accountKey || !this.accounts[accountKey]) {
      return null;
    }
    return this.accounts[accountKey];
  }

  /**
   * GraphQL 请求
   * Buffer API: https://api.buffer.com
   */
  async graphqlRequest(query, variables = {}, accountKey = 'account_a') {
    const account = this.accounts[accountKey];
    if (!account) {
      throw new Error(`Account ${accountKey} not found`);
    }

    const data = JSON.stringify({ query, variables });
    const url = new URL(this.baseUrl);

    // 如果有代理，通过代理发起请求
    if (this.proxyUrl) {
      return this.requestViaProxy(url, data, account);
    }

    // 直接请求
    return this.directRequest(url, data, account);
  }

  /**
   * 直接 HTTP/HTTPS 请求
   */
  directRequest(url, data, account) {
    return new Promise((resolve, reject) => {
      const options = {
        hostname: url.hostname,
        path: url.pathname + url.search,
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${account.access_token}`,
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(data)
        },
        timeout: 15000
      };

      const protocol = url.protocol === 'https:' ? https : http;
      const req = protocol.request(options, (res) => {
        let body = '';
        res.on('data', (chunk) => { body += chunk; });
        res.on('end', () => {
          try {
            const result = JSON.parse(body);
            if (result.errors) {
              resolve({ errors: result.errors });
            } else {
              resolve(result.data || result);
            }
          } catch (e) {
            resolve({ raw: body });
          }
        });
      });

      req.on('error', reject);
      req.on('timeout', () => { req.destroy(); reject(new Error('请求超时')); });
      req.write(data);
      req.end();
    });
  }

  /**
   * 通过代理发起请求
   */
  requestViaProxy(targetUrl, data, account) {
    return new Promise((resolve, reject) => {
      const proxyUrl = new URL(this.proxyUrl);
      const isHttps = targetUrl.protocol === 'https:';
      
      if (!isHttps) {
        reject(new Error('只支持 HTTPS 目标通过代理'));
        return;
      }

      // 使用 CONNECT 方法建立 TLS 隧道
      const connectOptions = {
        hostname: proxyUrl.hostname,
        port: proxyUrl.port || 8080,
        path: `${targetUrl.hostname}:443`,
        method: 'CONNECT',
        timeout: 10000
      };

      const proxyReq = http.request(connectOptions);
      proxyReq.on('connect', (res, socket) => {
        if (res.statusCode !== 200) {
          reject(new Error(`代理连接失败: HTTP ${res.statusCode}`));
          return;
        }

        // 通过隧道发送 HTTPS 请求
        const tlsOptions = {
          hostname: targetUrl.hostname,
          path: targetUrl.pathname,
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${account.access_token}`,
            'Content-Type': 'application/json',
            'Content-Length': Buffer.byteLength(data)
          },
          timeout: 15000,
          socket: socket
        };

        const tlsReq = https.request(tlsOptions, (tlsRes) => {
          let body = '';
          tlsRes.on('data', (chunk) => { body += chunk; });
          tlsRes.on('end', () => {
            try {
              const result = JSON.parse(body);
              socket.destroy();
              if (result.errors) {
                resolve({ errors: result.errors });
              } else {
                resolve(result.data || result);
              }
            } catch (e) {
              socket.destroy();
              resolve({ raw: body });
            }
          });
        });

        tlsReq.on('error', (e) => { socket.destroy(); reject(e); });
        tlsReq.on('timeout', () => { tlsReq.destroy(); reject(new Error('TLS 请求超时')); });
        tlsReq.write(data);
        tlsReq.end();
      });

      proxyReq.on('error', reject);
      proxyReq.on('timeout', () => { proxyReq.destroy(); reject(new Error('代理连接超时')); });
      proxyReq.end();
    });
  }

  /**
   * 获取指定账号的所有频道
   */
  async getChannels(accountKey = 'account_a') {
    const account = this.accounts[accountKey];
    if (!account) {
      throw new Error(`Account ${accountKey} not found`);
    }

    const query = `
      query GetChannels($input: ChannelsInput!) {
        channels(input: $input) {
          id
          service
          name
        }
      }
    `;

    const variables = {
      input: { organizationId: account.organization_id }
    };

    const result = await this.graphqlRequest(query, variables, accountKey);
    return result.channels || [];
  }

  /**
   * 获取所有账号的频道（用于诊断）
   */
  async getAllChannels() {
    const allChannels = {};
    for (const [accountKey, account] of Object.entries(this.accounts)) {
      try {
        const channels = await this.getChannels(accountKey);
        allChannels[accountKey] = {
          email: account.email,
          channels: channels
        };
      } catch (e) {
        allChannels[accountKey] = {
          email: account.email,
          error: e.message
        };
      }
    }
    return allChannels;
  }

  /**
   * 创建帖子到指定频道
   */
  async createPost(channelId, text, options = {}) {
    const { mediaUrl, accountKey, platform } = options;

    const query = `
      mutation CreatePost($input: CreatePostInput!) {
        createPost(input: $input) {
          __typename
          ... on PostActionSuccess {
            post { id text }
          }
          ... on MutationError {
            message
          }
        }
      }
    `;

    const postInput = {
      channelId,
      text,
      schedulingType: 'automatic',
      mode: 'shareNow'
    };

    // 所有平台都应附带媒体 (Pinterest/TikTok/YouTube 必须)
    if (mediaUrl) {
      postInput.assets = [{
        image: { url: mediaUrl }
      }];
    }

    // 平台特定的 metadata（修复各平台发布失败问题）
    if (platform) {
      postInput.metadata = this.buildPlatformMetadata(platform, text);
    }

    if (options.scheduledAt) {
      postInput.schedulingType = 'automatic';
      postInput.mode = 'customScheduled';
      postInput.dueAt = options.scheduledAt;
    }

    const variables = { input: postInput };
    const result = await this.graphqlRequest(query, variables, accountKey || 'account_a');

    // 正确解析响应
    if (result.errors) {
      return { success: false, error: result.errors.map(e => e.message).join(', ') };
    }

    const createPostResult = result.createPost;
    if (!createPostResult) {
      return { success: false, error: 'Unknown response format' };
    }

    if (createPostResult.__typename === 'MutationError' || createPostResult.message) {
      return { success: false, error: createPostResult.message || 'Unknown error' };
    }

    if (createPostResult.post) {
      return { success: true, post: createPostResult.post };
    }

    return { success: false, error: 'Unexpected response: ' + JSON.stringify(createPostResult).slice(0, 200) };
  }

  /**
   * 构建平台特定的 metadata
   * - Facebook: 必须指定 type (post/story/reel)
   * - Pinterest: 必须指定 boardServiceId
   * - TikTok: 可选 title
   */
  buildPlatformMetadata(platform, text) {
    const metadata = {};

    switch (platform) {
      case 'facebook':
        // Facebook 必须指定 type 字段，否则报错 "Facebook posts require a type"
        metadata.facebook = { type: 'post' };
        break;

      case 'pinterest':
        // Pinterest 必须指定 boardServiceId，否则报错 "no Pinterest board was selected"
        // boardServiceId 从配置文件或频道 metadata 获取
        const boardServiceId = this.getPinterestBoardServiceId();
        if (boardServiceId) {
          metadata.pinterest = {
            boardServiceId: boardServiceId,
            title: text.slice(0, 100) // Pinterest pin title
          };
        } else {
          console.log('   ⚠️ Pinterest: 未配置 boardServiceId，发布可能失败');
        }
        break;

      case 'tiktok':
        // TikTok 可选 title
        metadata.tiktok = {
          title: text.slice(0, 150)
        };
        break;
    }

    return Object.keys(metadata).length > 0 ? metadata : undefined;
  }

  /**
   * 获取 Pinterest board serviceId
   * 优先从配置文件读取，否则从 API 动态获取
   */
  getPinterestBoardServiceId() {
    // 从配置文件读取
    if (this.config.pinterest_board_service_id) {
      return this.config.pinterest_board_service_id;
    }
    // 缓存的值
    if (this._cachedBoardServiceId) {
      return this._cachedBoardServiceId;
    }
    // 返回默认的 "China Inbound Travel Guides" board
    return '719309440424840288';
  }

  /**
   * 动态获取 Pinterest boards 列表（用于选择 board）
   */
  async fetchPinterestBoards(accountKey = 'account_a') {
    const channels = await this.getChannels(accountKey);
    const pinterestChannel = channels.find(c => c.service === 'pinterest');

    if (!pinterestChannel) {
      return [];
    }

    const query = `
      query GetChannel($input: ChannelInput!) {
        channel(input: $input) {
          metadata {
            __typename
            ... on PinterestMetadata {
              boards {
                id
                name
                serviceId
              }
            }
          }
        }
      }
    `;

    try {
      const result = await this.graphqlRequest(query, {
        input: { id: pinterestChannel.id }
      }, accountKey);
      return result.channel?.metadata?.boards || [];
    } catch (e) {
      console.log('   ⚠️ 获取 Pinterest boards 失败:', e.message);
      return [];
    }
  }

  /**
   * 根据平台创建帖子（自动选择账号和频道）
   */
  async createPostForPlatform(platform, text, options = {}) {
    const accountKey = this.platformAccountMap[platform];
    if (!accountKey) {
      throw new Error(`No account configured for platform: ${platform}`);
    }

    const account = this.accounts[accountKey];
    
    // 先获取该账号的所有频道
    const channels = await this.getChannels(accountKey);
    
    // 查找对应平台的频道
    const serviceMap = {
      'facebook': 'facebook',
      'twitter': 'twitter',
      'linkedin': 'linkedin',
      'tiktok': 'tiktok',
      'youtube': 'youtube',
      'pinterest': 'pinterest'
    };
    
    const serviceName = serviceMap[platform];
    let channel = channels.find(c => c.service === serviceName);
    
    if (!channel) {
      throw new Error(`No ${platform} channel found for account ${accountKey}. Available: ${channels.map(c => c.name).join(', ')}`);
    }

    // 构建创建选项 - 始终传递封面图和平台信息
    const createOptions = {
      mediaUrl: options.mediaUrl,
      accountKey,
      scheduledAt: options.scheduledAt,
      platform  // 传递平台名称用于构建 metadata
    };

    // 必须带图的平台 (Pinterest, TikTok, YouTube)
    const platformsRequireMedia = ['pinterest', 'tiktok', 'youtube'];
    if (platformsRequireMedia.includes(platform) && !options.mediaUrl) {
      console.log(`   ⚠️  ${platform} requires media but none provided, attempting without...`);
    }

    const result = await this.createPost(channel.id, text, createOptions);
    
    return {
      success: result.success,
      platform,
      channelName: channel.name,
      accountEmail: account.email,
      post: result.post || null,
      error: result.error || null
    };
  }
}

module.exports = { BufferClient };