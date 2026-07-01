var __defProp = Object.defineProperty;
var __name = (target, value) => __defProp(target, "name", { value, configurable: true });

// worker.js
var BUFFER_ACCOUNTS = {
  A: {
    tokenKey: "BUFFER_WORKER_URL",
    name: "Buffer-A",
    channels: {
      x: { id: "6a202882c687a22dd45735b6", name: "fys2388", service: "twitter" },
      facebook: { id: "6a17e0c4c687a22dd4346d3c", name: "ChinaBound Travel", service: "facebook" },
      instagram: { id: "6a17e14dc687a22dd4346eb4", name: "joranchinatravel", service: "instagram" }
    },
    scheduleOffset: 0
    // EST 09:00/15:00
  },
  B: {
    tokenKey: "NEW_BUFFER_WORKER_URL",
    name: "Buffer-B",
    channels: {
      pinterest: { id: "6a21bdbec687a22dd45ec2ae", name: "Joranchinatravel", service: "pinterest" }
    },
    scheduleOffset: 11
    // EST 20:00 (比A晚11小时)
  }
};
var BUFFER_API_URL = "https://api.buffer.com";
var RATE_LIMIT = {
  GLOBAL_DAILY_MAX: 5,
  // 全局单日发布上限（支持多篇不同内容/配图的帖子）
  ACCOUNT_QUARTER_MAX: 70,
  // 单账户15分钟上限(官方100的70%安全阈值)
  QUOTA_WARNING_THRESHOLD: 0.3
  // 配额剩余30%触发预警
};
var RETRY_CONFIG = {
  MAX_RETRY: 3,
  BASE_DELAY: 2e3,
  JITTER: 1e3
};
var ALLOWED_IMAGE_HOST = "chinaboundtravel.com";
var ALLOWED_IMAGE_PATH = "/img/china-dest/";
var ALLOWED_EXTERNAL_HOSTS = ["image.pollinations.ai", "images.unsplash.com"];
var worker_default = {
  async fetch(request, env, ctx) {
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }
    const url = new URL(request.url);
    if (url.pathname === "/health") {
      return jsonResponse({
        status: "ok",
        service: "Buffer GraphQL Auto-Poster",
        version: "3.0.0",
        timestamp: (/* @__PURE__ */ new Date()).toISOString()
      });
    }
    if (url.pathname === "/channels") {
      return await handleQueryChannels(env);
    }
    if (url.pathname === "/publish" && request.method === "POST") {
      return await handlePublish(request, env, ctx);
    }
    if (url.pathname === "/retry-queue" && request.method === "POST") {
      return await processRetryQueue(env);
    }
    if (url.pathname === "/list-posts") {
      const query = `query GetScheduledPosts($input: PostsInput!) {
      posts(input: $input) {
        edges { node { id text dueAt isSent hasFailed channel { id name service } assets { type image { url } } } }
      }
    }`;
      const results = {};
      const tokenA = env.BUFFER_WORKER_URL || "";
      try {
        const resp = await fetch(BUFFER_API_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": `Bearer ${tokenA}` },
          body: JSON.stringify({
            query,
            variables: { input: { organizationId: "6a17ddf5e051bed5895272f0", sort: [{ field: "dueAt", direction: "asc" }], filter: { status: ["scheduled"] } } }
          })
        });
        results["Buffer-A"] = await resp.json();
      } catch (e) {
        results["Buffer-A"] = { error: e.message };
      }
      const tokenB = env.NEW_BUFFER_WORKER_URL || "";
      try {
        const resp = await fetch(BUFFER_API_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": `Bearer ${tokenB}` },
          body: JSON.stringify({
            query,
            variables: { input: { organizationId: "6a20329943b37a7289e25b6d", sort: [{ field: "dueAt", direction: "asc" }], filter: { status: ["scheduled"] } } }
          })
        });
        results["Buffer-B"] = await resp.json();
      } catch (e) {
        results["Buffer-B"] = { error: e.message };
      }
      return jsonResponse(results);
    }
    if (url.pathname === "/debug-boards") {
      const token = env.NEW_BUFFER_WORKER_URL || "";
      const queries = [
        { name: "pinterest_channels", query: 'query { channels(input: { organizationId: "6a20329943b37a7289e25b6d" }) { id name service metadata { ... on PinterestMetadata { boards { id name serviceId url } } } } }' },
        { name: "all_channels", query: 'query { channels(input: { organizationId: "6a20329943b37a7289e25b6d" }) { id name service } }' }
      ];
      const results = {};
      for (const q of queries) {
        try {
          const resp = await fetch(BUFFER_API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
            body: JSON.stringify({ query: q.query })
          });
          results[q.name] = await resp.json();
        } catch (e) {
          results[q.name] = { error: e.message };
        }
      }
      return jsonResponse(results);
    }
    if (url.pathname === "/reset-daily-count" && request.method === "POST") {
      const today = (/* @__PURE__ */ new Date()).toISOString().split("T")[0];
      const oldCount = await env.KV_STORE.get(`daily_count:${today}`);
      await env.KV_STORE.put(`daily_count:${today}`, "0");
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
    if (url.pathname === "/daily-count") {
      const today = (/* @__PURE__ */ new Date()).toISOString().split("T")[0];
      const count = await env.KV_STORE.get(`daily_count:${today}`);
      const quotaInfo = {};
      for (const [key, config] of Object.entries(BUFFER_ACCOUNTS)) {
        const quota = await env.KV_STORE.get(`account_quota:${key}`);
        quotaInfo[config.name] = quota || "no quota record";
      }
      return jsonResponse({
        date: today,
        daily_count: parseInt(count) || 0,
        daily_max: RATE_LIMIT.GLOBAL_DAILY_MAX,
        account_quotas: quotaInfo
      });
    }
    return jsonResponse({
      error: "Not Found",
      message: "Available endpoints: /health, /publish, /channels, /retry-queue, /reset-daily-count, /daily-count"
    }, 404);
  },
  /**
   * Cron定时任务处理
   * 触发规则：0 8 * * *（每日EST08:00重发积压任务）
   */
  async scheduled(event, env, ctx) {
    console.log(`[Cron] Triggered at ${new Date(event.scheduledTime).toISOString()}`);
    await processRetryQueue(env);
    return new Response("Cron executed");
  }
};
async function handlePublish(request, env, ctx) {
  try {
    const body = await request.json();
    const { title, desc, cover, url: postUrl } = body;
    if (!title || !desc) {
      return jsonResponse({
        success: false,
        error: "Missing required fields",
        message: "title and desc are required"
      }, 400);
    }
    let mediaUrl = cover || "";
    if (mediaUrl) {
      const isValid = validateImageUrl(mediaUrl);
      if (!isValid.valid) {
        return jsonResponse({
          success: false,
          error: "Image URL blocked",
          message: isValid.message
        }, 400);
      }
      mediaUrl = isValid.url;
    } else {
      return jsonResponse({
        success: false,
        error: "Missing cover image",
        message: `\u5FC5\u987B\u63D0\u4F9B cover \u5B57\u6BB5\uFF0C\u683C\u5F0F: https://${ALLOWED_IMAGE_HOST}${ALLOWED_IMAGE_PATH}\u5206\u7C7B/\u56FE\u7247.jpg`
      }, 400);
    }
    const dailyCount = await getDailyPublishCount(env);
    if (dailyCount >= RATE_LIMIT.GLOBAL_DAILY_MAX) {
      await saveToRetryQueue(env, { title, desc, cover, url: postUrl });
      return jsonResponse({
        success: false,
        error: "Daily limit exceeded",
        message: `\u4ECA\u65E5\u5DF2\u53D1\u5E03 ${dailyCount} \u7BC7\uFF0C\u5355\u65E5\u4E0A\u9650 ${RATE_LIMIT.GLOBAL_DAILY_MAX} \u7BC7\u3002\u7A3F\u4EF6\u5DF2\u5B58\u5165\u961F\u5217\uFF0C\u660E\u65E5\u81EA\u52A8\u53D1\u5E03\u3002`,
        queued: true
      }, 202);
    }
    const postText = body.custom_text || buildPostText(title, desc, postUrl);
    const allResults = {
      success: [],
      failed: [],
      details: []
    };
    for (const [accountKey, accountConfig] of Object.entries(BUFFER_ACCOUNTS)) {
      const accountQuota = await checkAccountQuota(env, accountKey);
      if (!accountQuota.allowed) {
        allResults.failed.push(...Object.keys(accountConfig.channels));
        allResults.details.push({
          platform: accountConfig.name,
          error: `\u8D26\u6237\u9650\u6D41: ${accountQuota.message}`
        });
        continue;
      }
      const token = env[accountConfig.tokenKey];
      if (!token) {
        allResults.failed.push(...Object.keys(accountConfig.channels));
        allResults.details.push({
          platform: accountConfig.name,
          error: "Token not configured"
        });
        continue;
      }
      const results = await publishToBuffer(
        Object.values(accountConfig.channels).map((c) => c.id),
        postText,
        mediaUrl,
        token,
        accountConfig.channels,
        env,
        accountKey,
        postUrl
      );
      allResults.success.push(...results.success);
      allResults.failed.push(...results.failed);
      allResults.details.push(...results.details);
      await updateAccountQuota(env, accountKey);
    }
    if (allResults.success.length > 0) {
      await incrementDailyPublishCount(env);
    }
    await sendFeishuNotification(env, {
      title: allResults.success.length > 0 ? "\u2705 \u793E\u5A92\u53D1\u5E03\u5B8C\u6210" : "\u26A0\uFE0F \u793E\u5A92\u53D1\u5E03\u5931\u8D25",
      content: `\u6587\u7AE0: ${title}
\u6210\u529F: ${allResults.success.join(", ") || "\u65E0"}
\u5931\u8D25: ${allResults.failed.join(", ") || "\u65E0"}`
    });
    return jsonResponse({
      success: allResults.success.length > 0,
      title,
      platforms: allResults,
      dailyCount: dailyCount + 1
    });
  } catch (error) {
    console.error("[Publish Error]", error);
    return jsonResponse({ success: false, error: error.message }, 500);
  }
}
__name(handlePublish, "handlePublish");
function validateImageUrl(url) {
  try {
    const parsed = new URL(url);
    if (url.startsWith("/")) {
      return { valid: true, url: `https://${ALLOWED_IMAGE_HOST}${url}` };
    }
    if (ALLOWED_EXTERNAL_HOSTS.includes(parsed.hostname)) {
      return { valid: true, url };
    }
    if (parsed.hostname !== ALLOWED_IMAGE_HOST) {
      return { valid: false, message: `\u56FE\u7247\u57DF\u540D\u5FC5\u987B\u662F ${ALLOWED_IMAGE_HOST} \u6216\u5141\u8BB8\u7684\u5916\u90E8\u670D\u52A1` };
    }
    if (!parsed.pathname.startsWith(ALLOWED_IMAGE_PATH)) {
      return { valid: false, message: `\u56FE\u7247\u8DEF\u5F84\u5FC5\u987B\u4EE5 ${ALLOWED_IMAGE_PATH} \u5F00\u5934` };
    }
    return { valid: true, url };
  } catch {
    return { valid: false, message: "\u65E0\u6548\u7684\u56FE\u7247URL\u683C\u5F0F" };
  }
}
__name(validateImageUrl, "validateImageUrl");
async function getDailyPublishCount(env) {
  const today = (/* @__PURE__ */ new Date()).toISOString().split("T")[0];
  const count = await env.KV_STORE.get(`daily_count:${today}`);
  return parseInt(count) || 0;
}
__name(getDailyPublishCount, "getDailyPublishCount");
async function incrementDailyPublishCount(env) {
  const today = (/* @__PURE__ */ new Date()).toISOString().split("T")[0];
  const count = await getDailyPublishCount(env);
  await env.KV_STORE.put(`daily_count:${today}`, (count + 1).toString());
}
__name(incrementDailyPublishCount, "incrementDailyPublishCount");
async function checkAccountQuota(env, accountKey) {
  const now = Date.now();
  const windowKey = Math.floor(now / (15 * 60 * 1e3));
  const key = `quota:${accountKey}:${windowKey}`;
  const count = await env.KV_STORE.get(key);
  const current = parseInt(count) || 0;
  if (current >= RATE_LIMIT.ACCOUNT_QUARTER_MAX) {
    return { allowed: false, message: `15\u5206\u949F\u5185\u5DF2\u8C03\u7528 ${current} \u6B21\uFF0C\u4E0A\u9650 ${RATE_LIMIT.ACCOUNT_QUARTER_MAX} \u6B21` };
  }
  return { allowed: true, remaining: RATE_LIMIT.ACCOUNT_QUARTER_MAX - current };
}
__name(checkAccountQuota, "checkAccountQuota");
async function updateAccountQuota(env, accountKey) {
  const now = Date.now();
  const windowKey = Math.floor(now / (15 * 60 * 1e3));
  const key = `quota:${accountKey}:${windowKey}`;
  const count = await env.KV_STORE.get(key);
  const current = parseInt(count) || 0;
  await env.KV_STORE.put(key, (current + 1).toString());
}
__name(updateAccountQuota, "updateAccountQuota");
async function saveToRetryQueue(env, postData) {
  const id = `retry:${Date.now()}:${Math.random().toString(36).substr(2, 9)}`;
  await env.KV_STORE.put(id, JSON.stringify(postData), {
    expirationTtl: 24 * 60 * 60
    // 24小时过期
  });
  console.log(`[Queue] Saved to retry queue: ${id}`);
}
__name(saveToRetryQueue, "saveToRetryQueue");
async function processRetryQueue(env) {
  console.log("[Queue] Processing retry queue...");
  let processed = 0;
  let success = 0;
  let failed = 0;
  const keys = await env.KV_STORE.list({ prefix: "retry:" });
  for (const key of keys.keys) {
    try {
      const data = await env.KV_STORE.get(key);
      if (!data)
        continue;
      const postData = JSON.parse(data);
      const dailyCount = await getDailyPublishCount(env);
      if (dailyCount >= RATE_LIMIT.GLOBAL_DAILY_MAX) {
        console.log("[Queue] Daily limit reached, stopping retry");
        break;
      }
      const body = new Request("http://localhost/publish", {
        method: "POST",
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
      await new Promise((r) => setTimeout(r, 1e3));
    } catch (error) {
      console.error("[Queue] Error processing:", error);
      failed++;
    }
  }
  const summary = { processed, success, failed };
  console.log(`[Queue] Retry completed: ${JSON.stringify(summary)}`);
  await sendFeishuNotification(env, {
    title: "\u{1F504} \u91CD\u8BD5\u961F\u5217\u5904\u7406\u5B8C\u6210",
    content: `\u5904\u7406: ${processed}
\u6210\u529F: ${success}
\u5931\u8D25: ${failed}`
  });
  return jsonResponse(summary);
}
__name(processRetryQueue, "processRetryQueue");
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
    const channelInfo = Object.values(channels).find((c) => c.id === channelId);
    const service = channelInfo?.service || "unknown";
    const now = /* @__PURE__ */ new Date();
    const offsetMs = (accountConfig.scheduleOffset || 0) * 36e5 + (channelIds.indexOf(channelId) + 1) * 72e5;
    const publishTime = new Date(now.getTime() + offsetMs);
    const baseInput = {
      channelId,
      schedulingType: "automatic",
      mode: "customScheduled",
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
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({ query: mutation, variables })
        });
        const remaining = parseInt(response.headers.get("X-RateLimit-Remaining") || "100");
        const limit = parseInt(response.headers.get("X-RateLimit-Limit") || "100");
        if (remaining / limit <= RATE_LIMIT.QUOTA_WARNING_THRESHOLD) {
          await sendFeishuNotification(env, {
            title: "\u26A0\uFE0F Buffer API\u914D\u989D\u9884\u8B66",
            content: `\u8D26\u6237: ${accountKey}
\u5E73\u53F0: ${service}
\u5269\u4F59\u914D\u989D: ${remaining}/${limit} (${(remaining / limit * 100).toFixed(0)}%)`
          });
        }
        if (!response.ok) {
          const errorText = await response.text();
          if (response.status === 429) {
            const retryAfter = parseInt(response.headers.get("Retry-After")) || 60;
            const delay = Math.pow(2, attempt) * RETRY_CONFIG.BASE_DELAY + Math.random() * RETRY_CONFIG.JITTER;
            console.log(`[RateLimit] ${service} - Retry after ${delay}ms (attempt ${attempt + 1})`);
            await new Promise((r) => setTimeout(r, Math.min(delay, retryAfter * 1e3)));
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
        if (service === "pinterest" && error.message.includes("Board ID") && attempt === 0) {
          console.log("[Pinterest] Board ID missing, querying boards...");
          const boardId = await queryPinterestBoardId(token);
          if (boardId) {
            console.log(`[Pinterest] Found board: ${boardId}`);
            env.PINTEREST_BOARD_SERVICE_ID = boardId;
            input = buildPlatformInput(service, text, mediaUrl, baseInput, env, postUrl);
            variables.input = input;
            attempt++;
            continue;
          }
        }
        if (!error.message.includes("429") && !error.message.includes("RATE_LIMIT")) {
          break;
        }
        attempt++;
        if (attempt < RETRY_CONFIG.MAX_RETRY) {
          const delay = Math.pow(2, attempt) * RETRY_CONFIG.BASE_DELAY;
          await new Promise((r) => setTimeout(r, delay));
        }
      }
    }
    if (!success) {
      results.failed.push(service);
      results.details.push({ platform: service, error: lastError?.message || "Unknown error" });
    }
  }
  return results;
}
__name(publishToBuffer, "publishToBuffer");
function buildPlatformInput(service, text, mediaUrl, baseInput, env, postUrl) {
  let input;
  if (service === "facebook") {
    const fbText = (text || "").slice(0, 5e3);
    input = {
      ...baseInput,
      text: fbText,
      metadata: { facebook: { type: "post" } },
      assets: mediaUrl ? [{ image: { url: mediaUrl } }] : []
    };
  } else if (service === "instagram") {
    const cleanText = (text || "").replace(/https?:\/\/[^\s]+/g, "").slice(0, 2200);
    input = {
      ...baseInput,
      text: cleanText,
      metadata: { instagram: { type: "post", shouldShareToFeed: true } },
      assets: [{ image: { url: mediaUrl } }]
    };
  } else if (service === "pinterest") {
    const pinTitle = (text || "").slice(0, 100);
    const pinBoardServiceId = env.PINTEREST_BOARD_SERVICE_ID || "719309440424840288";
    const pinLink = postUrl && postUrl.startsWith("http") ? postUrl : "https://chinaboundtravel.com";
    const pinMeta = {
      title: pinTitle,
      url: pinLink
    };
    if (pinBoardServiceId)
      pinMeta.boardServiceId = pinBoardServiceId;
    input = {
      ...baseInput,
      text: pinTitle,
      metadata: { pinterest: pinMeta },
      assets: [{ image: { url: mediaUrl } }]
    };
  } else {
    input = {
      ...baseInput,
      text: (text || "").slice(0, 280),
      assets: mediaUrl ? [{ image: { url: mediaUrl } }] : []
    };
  }
  return input;
}
__name(buildPlatformInput, "buildPlatformInput");
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
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ query })
    });
    const data = await response.json();
    const orgs = data.data?.account?.organizations || [];
    for (const org of orgs) {
      for (const channel of org.channels || []) {
        const boards = channel.metadata?.boards || [];
        if (boards.length > 0) {
          return boards[0].serviceId || boards[0].id;
        }
      }
    }
    console.log("[Pinterest] No boards found in channel metadata");
    return null;
  } catch (error) {
    console.error("[Pinterest Board Query Error]", error);
    return null;
  }
}
__name(queryPinterestBoardId, "queryPinterestBoardId");
function buildPostText(title, desc, postUrl) {
  const shortDesc = desc.length > 200 ? desc.substring(0, 200) + "..." : desc;
  const hashtags = "#ChinaTravel #ChinaTour #TravelTips";
  const link = postUrl ? `

\u{1F4D6} Read more: ${postUrl}` : "";
  return `${title}

${shortDesc}${link}

${hashtags}`;
}
__name(buildPostText, "buildPostText");
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
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
      body: JSON.stringify({ query })
    });
    const data = await response.json();
    const channels = [];
    const orgs = data.data?.account?.organizations || [];
    for (const org of orgs) {
      if (org.channels)
        channels.push(...org.channels);
    }
    return channels;
  } catch (error) {
    console.error("[Channel Query Error]", error);
    return [];
  }
}
__name(queryChannels, "queryChannels");
async function handleQueryChannels(env) {
  const allChannels = {};
  for (const [accountKey, accountConfig] of Object.entries(BUFFER_ACCOUNTS)) {
    const token = env[accountConfig.tokenKey];
    if (!token) {
      allChannels[accountKey] = { success: false, error: "Token not configured" };
      continue;
    }
    const channels = await queryChannels(token);
    allChannels[accountKey] = { success: true, channels };
  }
  return jsonResponse({ success: true, accounts: allChannels });
}
__name(handleQueryChannels, "handleQueryChannels");
async function sendFeishuNotification(env, data) {
  if (!env.FEISHU_WEBHOOK_URL)
    return;
  try {
    await fetch(env.FEISHU_WEBHOOK_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        msg_type: "post",
        content: {
          post: {
            zh_cn: { title: data.title, content: [[{ tag: "text", text: data.content }]] }
          }
        }
      })
    });
  } catch (error) {
    console.error("[Feishu Error]", error);
  }
}
__name(sendFeishuNotification, "sendFeishuNotification");
function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: { "Content-Type": "application/json", ...corsHeaders() }
  });
}
__name(jsonResponse, "jsonResponse");
function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization"
  };
}
__name(corsHeaders, "corsHeaders");
export {
  worker_default as default
};
//# sourceMappingURL=worker.js.map
