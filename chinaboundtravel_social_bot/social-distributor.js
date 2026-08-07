/**
 * ChinaBound Travel - 社媒分发器 (Node.js 版本)
 * 支持双账号 Buffer 配置
 */

const fs = require('fs');
const path = require('path');
const { BufferClient } = require('./buffer-client');

// 配置路径
const CONFIG_PATH = path.join(__dirname, 'buffer_config.json');
const POSTS_DIR = path.join(__dirname, '..', 'content', 'posts');
const MANIFEST_PATH = path.join(__dirname, 'distribution_manifest.json');
const SITE_URL = 'https://www.chinaboundtravel.com';

// 平台标签配置
const PLATFORM_HASHTAGS = {
  facebook: '#ChinaTravel #China #VisitChina #TravelTips #ChinaBoundTravel',
  twitter: '#ChinaTravel #China #Travel #VisitChina',
  linkedin: '#ChinaTravel #TravelIndustry #ChinaTourism #DigitalNomad',
  tiktok: '#ChinaTravel #VisitChina #ChinaTrip #TravelChina',
  youtube: '',
  pinterest: '#ChinaTravel #China #TravelPhotography #VisitChina'
};

// 可用平台列表
const AVAILABLE_PLATFORMS = ['twitter', 'pinterest', 'tiktok', 'facebook', 'youtube'];

// YouTube 需要视频内容，Buffer API 无法直接发布视频
const API_UNSUPPORTED_PLATFORMS = ['youtube'];

class SocialDistributor {
  constructor() {
    this.bufferClient = new BufferClient(CONFIG_PATH);
    this.manifest = this.loadManifest();
  }

  /**
   * 加载发布记录清单
   */
  loadManifest() {
    try {
      if (fs.existsSync(MANIFEST_PATH)) {
        return JSON.parse(fs.readFileSync(MANIFEST_PATH, 'utf-8'));
      }
    } catch (e) {
      console.warn('⚠️ Manifest 读取失败，创建新的:', e.message);
    }
    return { published: {} };
  }

  /**
   * 保存发布记录
   */
  saveManifest() {
    fs.writeFileSync(MANIFEST_PATH, JSON.stringify(this.manifest, null, 2), 'utf-8');
  }

  /**
   * 获取指定平台已发布的文章列表
   */
  getPublishedSlugs(platform) {
    const published = this.manifest.published[platform] || [];
    // 清理：只保留 slug（过滤时间戳）
    return published.filter(item => !item.match(/^\d{4}-\d{2}-\d{2}T/));
  }

  /**
   * 标记文章为已发布
   */
  markAsPublished(platform, slug) {
    if (!this.manifest.published[platform]) {
      this.manifest.published[platform] = [];
    }
    this.manifest.published[platform].push(slug);
    this.manifest.published[platform].push(new Date().toISOString());
    this.saveManifest();
  }

  /**
   * 解析 Markdown Frontmatter
   */
  parseFrontmatter(content) {
    if (!content.startsWith('---')) return {};
    
    const fmEnd = content.indexOf('---', 3);
    if (fmEnd === -1) return {};
    
    const fmText = content.substring(3, fmEnd).trim();
    const frontmatter = {};
    let currentList = null;
    let currentMap = null;
    let currentMapKey = null;
    
    for (const line of fmText.split('\n')) {
      const stripped = line.trim();
      
      if (!stripped) continue;
      
      // 嵌套 map 条目
      if (line.startsWith('  ') && currentMap !== null) {
        if (stripped.includes(': ')) {
          const [key, ...rest] = stripped.split(': ');
          const value = rest.join(': ').trim().replace(/^["']|["']$/g, '');
          currentMap[key.trim()] = value;
        }
        continue;
      }
      
      // 列表项
      if (stripped.startsWith('- ')) {
        if (currentList !== null) {
          currentList.push(stripped.substring(2).replace(/^["']|["']$/g, ''));
        }
        continue;
      }
      
      if (stripped.includes(': ')) {
        const [key, ...rest] = stripped.split(': ');
        const value = rest.join(': ').trim().replace(/^["']|["']$/g, '');
        
        if (value.startsWith('[') && value.endsWith(']')) {
          const listItems = value.slice(1, -1).split(',').map(v => v.trim().replace(/^["']|["']$/g, ''));
          frontmatter[key.trim()] = listItems;
          currentList = listItems;
          currentMap = null;
          currentMapKey = null;
        } else {
          frontmatter[key.trim()] = value;
          currentList = null;
          currentMap = null;
          currentMapKey = null;
        }
      } else if (stripped.endsWith(':')) {
        const key = stripped.slice(0, -1).trim();
        currentMap = {};
        frontmatter[key] = currentMap;
        currentMapKey = key;
        currentList = null;
      }
    }
    
    return frontmatter;
  }

  /**
   * 获取最新未发布的文章
   */
  getUnpublishedPosts(platform, limit = 3) {
    const publishedSlugs = new Set(this.getPublishedSlugs(platform));
    const posts = [];
    
    // 获取所有 .md 文件并按文件名排序（文件名包含日期，所以按名字倒序即可）
    const files = fs.readdirSync(POSTS_DIR)
      .filter(f => f.endsWith('.md') && !f.startsWith('.'))
      .sort()
      .reverse();
    
    for (const file of files) {
      const slug = path.basename(file, '.md');
      
      // 跳过已发布的
      if (publishedSlugs.has(slug)) continue;
      
      // 跳过月度更新文章
      if (slug.includes('monthly-update') || slug.includes('monthly_update')) continue;
      
      // 读取并解析文件
      const filePath = path.join(POSTS_DIR, file);
      const content = fs.readFileSync(filePath, 'utf-8');
      const fm = this.parseFrontmatter(content);
      
      // 跳过草稿
      if (fm.draft === true) continue;
      
      const title = fm.title || '';
      if (!title) continue;
      
      // 获取封面图 URL
      let coverUrl = '';
      if (typeof fm.cover === 'string') {
        coverUrl = fm.cover;
      } else if (fm.cover && fm.cover.image) {
        coverUrl = fm.cover.image;
      }
      
      posts.push({
        slug,
        title,
        description: fm.description || '',
        summary: fm.summary || fm.description || '',
        cover: coverUrl,
        categories: Array.isArray(fm.categories) ? fm.categories : [],
        tags: Array.isArray(fm.tags) ? fm.tags : [],
        date: fm.date || '',
        url: `${SITE_URL}/posts/${fm.slug || slug}/`
      });
      
      if (posts.length >= limit) break;
    }
    
    return posts;
  }

  /**
   * 为不同平台生成文案
   */
  generateSocialText(post, platform) {
    const { title, url, summary } = post;
    const hashtags = PLATFORM_HASHTAGS[platform] || '';
    
    switch (platform) {
      case 'twitter':
        return {
          text: `${title}\n\n${summary.slice(0, 100)}...\n\n${url}\n${hashtags}`,
          coverUrl: post.cover
        };
        
      case 'facebook':
        return {
          text: `✈️ ${title}\n\n${summary}\n\nRead the full guide: ${url}\n\n${hashtags}`,
          coverUrl: post.cover
        };
        
      case 'linkedin':
        return {
          text: `New on ChinaBound Travel! 🇨🇳\n\n${title}\n\n${summary}\n\nRead the full guide: ${url}\n\n${hashtags}`,
          coverUrl: post.cover
        };
        
      case 'tiktok':
        return {
          text: `${title}\n\n${summary.slice(0, 150)}... Link in bio: ${url}\n\n${hashtags}`,
          coverUrl: post.cover
        };
        
      case 'pinterest':
        return {
          text: `${title}\n\n${summary}\n\n${url}\n\n${hashtags}`,
          coverUrl: post.cover
        };
        
      case 'youtube':
        return {
          text: `${title}\n\n${summary}\n\n${url}`,
          coverUrl: post.cover
        };
        
      default:
        return {
          text: `${title}\n\n${summary}\n\n${url}\n\n${hashtags}`,
          coverUrl: post.cover
        };
    }
  }

  /**
   * 分发到所有平台
   */
  async distribute(options = {}) {
    const platforms = options.platforms || AVAILABLE_PLATFORMS;
    const limit = options.limit || 3;
    const dryRun = options.dryRun || false;
    
    console.log('🚀 ChinaBound Social Distributor (Node.js)');
    console.log(`   平台: ${platforms.join(', ')}`);
    console.log(`   每平台数量: ${limit}`);
    console.log(`   模拟模式: ${dryRun ? '开启' : '关闭'}`);
    console.log();
    
    const results = {};
    
    for (const platform of platforms) {
      console.log(`\n📱 处理 ${platform}...`);
      
      // 检查平台是否已配置
      const accountKey = this.bufferClient.platformAccountMap[platform];
      if (!accountKey) {
        console.log(`   ⚠️ 平台 ${platform} 未配置账号，跳过`);
        results[platform] = { status: 'skipped', reason: 'no_account' };
        continue;
      }
      
      // 检查 API 是否支持该平台
      if (API_UNSUPPORTED_PLATFORMS.includes(platform)) {
        console.log(`   ⚠️ 平台 ${platform} 暂不支持 API 发布，需手动处理`);
        results[platform] = { status: 'skipped', reason: 'api_unsupported' };
        continue;
      }
      
      const posts = this.getUnpublishedPosts(platform, limit);
      
      if (posts.length === 0) {
        console.log(`   ✅ ${platform} 没有未发布的文章`);
        results[platform] = { status: 'no_posts' };
        continue;
      }
      
      console.log(`   📝 找到 ${posts.length} 篇待发布文章:`);
      posts.forEach((p, i) => {
        console.log(`      ${i + 1}. ${p.title.slice(0, 60)}`);
      });
      
      const platformResults = [];
      
      for (const post of posts) {
        try {
          const socialContent = this.generateSocialText(post, platform);
          
          if (dryRun) {
            console.log(`   🔇 [模拟] 将发布到 ${platform}: ${post.title.slice(0, 50)}...`);
            console.log(`      文案: ${socialContent.text.slice(0, 80)}...`);
            platformResults.push({
              slug: post.slug,
              success: true,
              dryRun: true
            });
            continue;
          }
          
          // YouTube 需要视频，跳过
          if (platform === 'youtube') {
            console.log(`   ⚠️ YouTube 需要视频内容，跳过文章发布`);
            platformResults.push({
              slug: post.slug,
              success: false,
              reason: 'youtube_needs_video'
            });
            continue;
          }
          
          // Pinterest/TikTok 需要图片
          if ((platform === 'pinterest' || platform === 'tiktok') && !post.cover) {
            console.log(`   ⚠️ ${platform} 需要封面图，跳过（无可用封面）`);
            platformResults.push({
              slug: post.slug,
              success: false,
              reason: 'no_cover_image'
            });
            continue;
          }
          
          console.log(`   📤 发布中...`);
          const result = await this.bufferClient.createPostForPlatform(
            platform,
            socialContent.text,
            { mediaUrl: socialContent.coverUrl || undefined }
          );

          if (result.success) {
            // 验证发布状态（等待10秒后查询实际状态）
            console.log(`   ⏳ 验证发布状态...`);
            const postId = result.post?.id;
            let actualStatus = 'created'; // 默认为已创建
            let errorMsg = null;

            if (postId) {
              await new Promise(resolve => setTimeout(resolve, 10000));
              const verification = await this.verifyPostStatus(platform, postId);
              actualStatus = verification.status;
              errorMsg = verification.error;
            }

            if (actualStatus === 'sent') {
              console.log(`   ✅ 发布成功: ${post.title.slice(0, 50)} -> ${platform}`);
              this.markAsPublished(platform, post.slug);
              platformResults.push({
                slug: post.slug,
                success: true,
                channelName: result.channelName,
                accountEmail: result.accountEmail,
                verified: true
              });
            } else if (actualStatus === 'error') {
              console.log(`   ❌ 发布失败（平台拒绝）: ${errorMsg || '未知错误'}`);
              // 不标记为已发布，允许重试
              platformResults.push({
                slug: post.slug,
                success: false,
                error: errorMsg || 'platform_rejected',
                postId: postId
              });
            } else {
              // scheduled 或 sending 状态 - 标记为已创建但未验证
              console.log(`   📝 已创建到队列（状态: ${actualStatus}）: ${post.title.slice(0, 50)} -> ${platform}`);
              this.markAsPublished(platform, post.slug);
              platformResults.push({
                slug: post.slug,
                success: true,
                channelName: result.channelName,
                accountEmail: result.accountEmail,
                verified: false,
                status: actualStatus
              });
            }
          } else {
            console.log(`   ❌ 发布失败: ${result.error || '未知错误'}`);
            platformResults.push({
              slug: post.slug,
              success: false,
              error: result.error || 'unknown'
            });
          }
          
          // 等待 2 秒避免速率限制
          if (!dryRun) {
            await new Promise(resolve => setTimeout(resolve, 2000));
          }
          
        } catch (e) {
          console.log(`   ❌ 异常: ${e.message}`);
          platformResults.push({
            slug: post.slug,
            success: false,
            error: e.message
          });
        }
      }
      
      results[platform] = {
        status: 'completed',
        posts: platformResults
      };
    }
    
    // 汇总
    console.log('\n📊 发布汇总:');
    for (const [platform, result] of Object.entries(results)) {
      if (result.posts) {
        const successCount = result.posts.filter(p => p.success).length;
        const failCount = result.posts.filter(p => !p.success).length;
        console.log(`   ${platform}: ✅ ${successCount} 成功, ❌ ${failCount} 失败`);
      } else {
        console.log(`   ${platform}: ${result.status}`);
      }
    }
    
    return results;
  }

  /**
   * 验证帖子在平台上的实际发布状态
   * 查询 Buffer API 获取 post 的 status 字段
   */
  async verifyPostStatus(platform, postId) {
    const accountKey = this.bufferClient.platformAccountMap[platform];
    if (!accountKey) {
      return { status: 'unknown', error: 'No account configured' };
    }

    const query = `
      query GetPost($input: PostInput!) {
        post(input: $input) {
          id
          status
          sentAt
          error { message }
        }
      }
    `;

    try {
      const result = await this.bufferClient.graphqlRequest(query, {
        input: { id: postId }
      }, accountKey);

      if (result.errors) {
        return { status: 'unknown', error: result.errors[0].message };
      }

      const post = result.post;
      if (!post) {
        return { status: 'unknown', error: 'Post not found' };
      }

      return {
        status: post.status, // sent, error, scheduled, sending, draft
        error: post.error?.message || null,
        sentAt: post.sentAt
      };
    } catch (e) {
      return { status: 'unknown', error: e.message };
    }
  }

  /**
   * 诊断模式 - 检查连接和状态
   */
  async diagnose() {
    console.log('🔍 Buffer 双账号诊断\n');
    
    // 1. 检查配置
    console.log('1️⃣ 检查配置...');
    console.log(`   Account A: ${this.bufferClient.accounts.account_a.email}`);
    console.log(`   Account B: ${this.bufferClient.accounts.account_b.email}`);
    
    // 2. 测试连接
    console.log('\n2️⃣ 测试 API 连接...');
    try {
      const allChannels = await this.bufferClient.getAllChannels();
      
      for (const [accountKey, info] of Object.entries(allChannels)) {
        console.log(`\n   ${accountKey} (${info.email}):`);
        if (info.error) {
          console.log(`      ❌ 错误: ${info.error}`);
        } else if (info.channels.length > 0) {
          console.log(`      ✅ ${info.channels.length} 个频道:`);
          info.channels.forEach(ch => {
            console.log(`         - ${ch.name} (${ch.service})`);
          });
        } else {
          console.log(`      ⚠️  无频道`);
        }
      }
    } catch (e) {
      console.log(`   ❌ 连接失败: ${e.message}`);
    }
    
    // 3. 检查发布状态
    console.log('\n3️⃣ 检查发布状态...');
    for (const platform of AVAILABLE_PLATFORMS) {
      const published = this.getPublishedSlugs(platform);
      const unpublished = this.getUnpublishedPosts(platform, 1);
      console.log(`   ${platform}: 已发布 ${published.length} 篇, 待发布 ${unpublished.length}+ 篇`);
    }
    
    console.log('\n✅ 诊断完成');
  }
}

// 主程序
async function main() {
  const distributor = new SocialDistributor();
  const args = process.argv.slice(2);
  
  const helpText = `
用法: node social-distributor.js [命令] [选项]

命令:
  diagnose    诊断 Buffer 连接和配置
  distribute  分发文章到社媒平台
  list        列出待发布的文章

选项:
  --platforms=facebook,twitter,pinterest,tiktok  指定平台
  --limit=3   每平台发布数量 (默认: 3)
  --dry-run   模拟运行，不实际发布

示例:
  node social-distributor.js diagnose
  node social-distributor.js list
  node social-distributor.js distribute --platforms=facebook,twitter --limit=2 --dry-run
  node social-distributor.js distribute --platforms=pinterest,tiktok --limit=1
`;
  
  const command = args[0] || 'help';
  
  // 解析选项
  const options = {
    platforms: AVAILABLE_PLATFORMS,
    limit: 3,
    dryRun: false
  };
  
  for (const arg of args.slice(1)) {
    if (arg === '--dry-run') options.dryRun = true;
    else if (arg.startsWith('--platforms=')) {
      options.platforms = arg.split('=')[1].split(',');
    } else if (arg.startsWith('--limit=')) {
      options.limit = parseInt(arg.split('=')[1], 10);
    }
  }
  
  switch (command) {
    case 'diagnose':
      await distributor.diagnose();
      break;
      
    case 'distribute':
      await distributor.distribute(options);
      break;
      
    case 'list':
      console.log('📋 待发布文章列表:\n');
      for (const platform of options.platforms) {
        const posts = distributor.getUnpublishedPosts(platform, 5);
        console.log(`\n📱 ${platform}:`);
        if (posts.length === 0) {
          console.log('   全部已发布 ✅');
        } else {
          posts.forEach((p, i) => {
            console.log(`   ${i + 1}. ${p.title.slice(0, 60)}`);
            console.log(`      URL: ${p.url}`);
            console.log(`      封面: ${p.cover || '无'}`);
          });
        }
      }
      break;
      
    case 'help':
    default:
      console.log(helpText);
  }
}

main().catch(console.error);