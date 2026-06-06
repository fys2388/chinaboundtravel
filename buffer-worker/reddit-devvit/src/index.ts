/**
 * ChinaBoundTravel Reddit 自动发帖机器人
 * 
 * 功能：
 * 1. 双 Cron 定时任务：UTC14:00(EST09:00) / UTC20:00(EST15:00)
 * 2. 单日上限 2 帖
 * 3. 从网站 JSON 接口读取文章数据
 * 4. 自动发布到 r/ChinaTravel
 * 
 * 使用：
 * 1. npm create devvit@latest 创建项目
 * 2. 替换本文件内容
 * 3. npm run dev 测试
 * 4. npm run deploy 部署到 Reddit
 */

import { Devvit, useState } from '@devvit/public-api';

// ============ 配置常量 ============

const CONFIG = {
  // 发布配置
  DAILY_LIMIT: 2,                    // 单日发布上限
  SUBREDDIT: 'ChinaTravel',           // 发布目标 subreddit
  USER_AGENT: 'ChinaBoundTravel/1.0', // Reddit API User-Agent
  
  // Cron 时间（UTC）
  // UTC14:00 = EST 09:00（上午）
  // UTC20:00 = EST 15:00（下午）
  CRON_MORNING: '0 14 * * *',  // EST 09:00
  CRON_AFTERNOON: '0 20 * * *', // EST 15:00
  
  // JSON 接口地址
  JSON_LATEST: 'https://chinaboundtravel.com/api/reddit-latest.json',
  JSON_SECOND: 'https://chinaboundtravel.com/api/reddit-second.json',
};

// ============ 类型定义 ============

interface RedditPost {
  title: string;
  desc: string;
  url: string;
  cover: string;
  date: string;
  slug: string;
}

interface DailyStats {
  count: number;
  lastPostDate: string;
  postedSlugs: string[];
}

// ============ 存储键 ============

const STORAGE_KEYS = {
  DAILY_STATS: 'daily_stats',
};

// ============ 帮助函数 ============

/**
 * 获取今日日期字符串 (YYYY-MM-DD)
 */
function getToday(): string {
  return new Date().toISOString().split('T')[0];
}

/**
 * 从 JSON 接口获取文章数据
 */
async function fetchPost(url: string): Promise<RedditPost | null> {
  try {
    const response = await fetch(url);
    if (!response.ok) {
      console.error(`Failed to fetch ${url}: ${response.status}`);
      return null;
    }
    return await response.json();
  } catch (error) {
    console.error(`Error fetching ${url}:`, error);
    return null;
  }
}

/**
 * 构建 Reddit 帖子内容
 */
function buildPostContent(post: RedditPost): string {
  const desc = post.desc.length > 400 
    ? post.desc.substring(0, 400) + '...' 
    : post.desc;
  
  const content = `
**${post.title}**

${desc}

---

**Read the full guide:** [chinaboundtravel.com](${post.url})

---

*I'm Joran, an American from California who's been living in and traveling through China for over 10 years. Ask me anything about visiting China!*

#ChinaTravel #VisitChina #ChinaTourism #TravelGuide
`;
  
  return content;
}

/**
 * 获取并验证今日发布统计
 */
async function getDailyStats(context: Devvit.Context): Promise<DailyStats> {
  const today = getToday();
  
  const statsStr = await context.kvStore.get<string>(STORAGE_KEYS.DAILY_STATS);
  if (!statsStr) {
    return { count: 0, lastPostDate: today, postedSlugs: [] };
  }
  
  try {
    const stats: DailyStats = JSON.parse(statsStr);
    
    // 如果日期变了，重置统计
    if (stats.lastPostDate !== today) {
      return { count: 0, lastPostDate: today, postedSlugs: [] };
    }
    
    return stats;
  } catch {
    return { count: 0, lastPostDate: today, postedSlugs: [] };
  }
}

/**
 * 检查是否应该发帖（防重复发布核心逻辑）
 */
async function shouldPost(
  context: Devvit.Context, 
  postSlug: string
): Promise<{ should: boolean; stats: DailyStats; reason: string }> {
  const stats = await getDailyStats(context);
  
  // 检查是否已达单日上限
  if (stats.count >= CONFIG.DAILY_LIMIT) {
    return { 
      should: false, 
      stats,
      reason: `Daily limit reached (${stats.count}/${CONFIG.DAILY_LIMIT})` 
    };
  }
  
  // 检查是否已发布过同一篇文章（防重复）
  if (stats.postedSlugs.includes(postSlug)) {
    return { 
      should: false, 
      stats,
      reason: `Already posted: ${postSlug}` 
    };
  }
  
  return { should: true, stats, reason: 'OK' };
}

/**
 * 更新发布统计
 */
async function updateStats(context: Devvit.Context, stats: DailyStats, slug: string): Promise<void> {
  stats.count += 1;
  stats.postedSlugs.push(slug);
  await context.kvStore.put(STORAGE_KEYS.DAILY_STATS, JSON.stringify(stats));
}

/**
 * 发布到 Reddit
 */
async function postToReddit(
  context: Devvit.Context, 
  post: RedditPost
): Promise<{ success: boolean; postId?: string }> {
  try {
    const content = buildPostContent(post);
    
    const response = await context.reddit.submitPost({
      subredditName: CONFIG.SUBREDDIT,
      title: post.title.substring(0, 300),
      text: content,
    });
    
    if (response?.id) {
      return { success: true, postId: response.id };
    }
    
    return { success: false };
  } catch (error) {
    console.error('Failed to post to Reddit:', error);
    return { success: false };
  }
}

// ============ Cron 定时任务：上午 (EST 09:00 / UTC 14:00) ============

Devvit.addTrigger({
  event: 'ScheduledPost',
  cron: CONFIG.CRON_MORNING,
  async handler(event, context) {
    console.log(`[Morning Cron] Running at ${new Date().toISOString()}`);
    
    // 获取文章数据
    const post = await fetchPost(CONFIG.JSON_LATEST);
    if (!post) {
      console.log('[Morning Cron] Failed to fetch latest post');
      return;
    }
    
    // 检查是否应该发帖（防重复）
    const { should, stats, reason } = await shouldPost(context, post.slug);
    if (!should) {
      console.log(`[Morning Cron] Skipping: ${reason}`);
      return;
    }
    
    // 发布
    const { success, postId } = await postToReddit(context, post);
    
    if (success && postId) {
      console.log(`[Morning Cron] Posted successfully: ${postId}`);
      await updateStats(context, stats, post.slug);
    } else {
      console.log('[Morning Cron] Post failed');
    }
  },
});

// ============ Cron 定时任务：下午 (EST 15:00 / UTC 20:00) ============

Devvit.addTrigger({
  event: 'ScheduledPost',
  cron: CONFIG.CRON_AFTERNOON,
  async handler(event, context) {
    console.log(`[Afternoon Cron] Running at ${new Date().toISOString()}`);
    
    // 获取文章数据
    const post = await fetchPost(CONFIG.JSON_SECOND);
    if (!post) {
      console.log('[Afternoon Cron] Failed to fetch second post');
      return;
    }
    
    // 检查是否应该发帖（防重复）
    const { should, stats, reason } = await shouldPost(context, post.slug);
    if (!should) {
      console.log(`[Afternoon Cron] Skipping: ${reason}`);
      return;
    }
    
    // 发布
    const { success, postId } = await postToReddit(context, post);
    
    if (success && postId) {
      console.log(`[Afternoon Cron] Posted successfully: ${postId}`);
      await updateStats(context, stats, post.slug);
    } else {
      console.log('[Afternoon Cron] Post failed');
    }
  },
});

// ============ 手动触发测试命令 ============

Devvit.addCommand({
  name: 'post-now',
  description: '手动发布一篇文章到 Reddit',
  options: [
    {
      name: 'post-type',
      description: '发布类型: latest 或 second',
      type: 'string',
      required: true,
    },
  ],
  async handler(command, context) {
    const postType = command.options['post-type'];
    const url = postType === 'latest' ? CONFIG.JSON_LATEST : CONFIG.JSON_SECOND;
    
    const post = await fetchPost(url);
    if (!post) {
      return `Failed to fetch ${postType} post`;
    }
    
    const { should, stats, reason } = await shouldPost(context, post.slug);
    if (!should) {
      return `Cannot post: ${reason}`;
    }
    
    const { success, postId } = await postToReddit(context, post);
    
    if (success && postId) {
      await updateStats(context, stats, post.slug);
      return `Posted successfully: https://reddit.com/r/${CONFIG.SUBREDDIT}/comments/${postId}`;
    }
    
    return 'Post failed';
  },
});

// ============ 状态检查命令 ============

Devvit.addCommand({
  name: 'status',
  description: '查看今日发布状态',
  async handler(command, context) {
    const stats = await getDailyStats(context);
    return `
Today: ${stats.lastPostDate}
Posted: ${stats.count}/${CONFIG.DAILY_LIMIT}
Posted slugs: ${stats.postedSlugs.join(', ') || 'None'}
    `.trim();
  },
});

// ============ 重置每日计数命令 ============

Devvit.addCommand({
  name: 'reset-stats',
  description: '重置今日发布计数',
  async handler(command, context) {
    const today = getToday();
    await context.kvStore.put(STORAGE_KEYS.DAILY_STATS, JSON.stringify({
      count: 0,
      lastPostDate: today,
      postedSlugs: [],
    }));
    return 'Daily stats reset';
  },
});

// ============ 导出 ============

export default Devvit;