/**
 * SenseNova LLM 客户端 — 生成 Buffer 社区评论回复
 * 端点：https://token.sensenova.cn/v1/chat/completions（OpenAI 兼容）
 * 模型：sensenova-6.8-flash-lite
 */
const DEFAULT_BASE_URL = 'https://token.sensenova.cn/v1';
const DEFAULT_MODEL = 'sensenova-6.8-flash-lite';

/**
 * 用 SenseNova 为一条评论生成英文回复（≤280 字符）
 * @param {object} p
 * @param {string} p.commentText 客户评论原文
 * @param {string} p.commenter 评论者用户名
 * @param {string} p.postText 帖子正文（用于语境）
 * @param {string} p.brandContext 品牌语境提示
 * @param {string} p.charLimit 字符上限（默认 280）
 * @param {string} p.apiKey SenseNova API Key（从 SENSENOVA_API_KEY 注入）
 * @param {string} p.model
 * @param {string} p.baseUrl
 * @returns {Promise<string>} 生成的回复文本
 */
export async function generateReply({
  commentText,
  commenter = '',
  postText = '',
  brandContext = '',
  charLimit = 280,
  apiKey = '',
  model = DEFAULT_MODEL,
  baseUrl = DEFAULT_BASE_URL,
}) {
  if (!apiKey) {
    throw new Error('SENSENOVA_API_KEY 未配置，无法生成回复');
  }

  const system = [
    '你是 ChinaBound Travel（中国旅行指南品牌）的社媒运营助手。',
    brandContext,
    `请为下面这条客户评论写一条自然、友好、有信息量的英文回复。`,
    `硬性要求：只输出回复正文，不要任何引号/前缀/解释；全文不超过 ${charLimit} 字符；语气契合品牌；如评论含提问则正面回答，如只是好评则真诚感谢并补充一点实用信息。`,
  ].filter(Boolean).join('\n');

  const user = [
    `帖子正文（供语境参考）：${(postText || '').slice(0, 600)}`,
    ``,
    `评论者：${commenter || '匿名'}`,
    `评论内容：${commentText}`,
  ].join('\n');

  const body = {
    model,
    messages: [
      { role: 'system', content: system },
      { role: 'user', content: user },
    ],
    temperature: 0.7,
    max_tokens: 500,
  };

  const resp = await fetch(`${baseUrl.replace(/\/$/, '')}/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify(body),
  });

  if (!resp.ok) {
    const text = await resp.text().catch(() => '');
    throw new Error(`SenseNova 请求失败 HTTP ${resp.status}: ${text.slice(0, 300)}`);
  }

  const data = await resp.json();
  const reply = data?.choices?.[0]?.message?.content?.trim();
  if (!reply) {
    throw new Error('SenseNova 未返回内容');
  }
  return reply.slice(0, charLimit);
}
