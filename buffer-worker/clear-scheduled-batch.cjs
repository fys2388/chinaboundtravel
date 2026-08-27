// 清理当天自动排期批次（按 dueAt 范围），dry-run 默认只列出不删除。
const https = require('https');

const DRY_RUN = process.env.DRY_RUN !== '0';
const FROM_UTC = process.env.FROM_UTC || '2026-08-27T00:00:00Z';
const TO_UTC = process.env.TO_UTC || '2026-08-29T00:00:00Z';
const TOKENS = [
  process.env.BUFFER_API_TOKEN_A,
  process.env.BUFFER_API_TOKEN_B,
].map((s) => (s || '').trim()).filter(Boolean);

function queryBuffer(token, query) {
  const bearer = 'Bearer ' + token.trim();
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'api.buffer.com',
      port: 443,
      path: '/',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': bearer,
      },
    };
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          if (json.errors) reject(new Error(JSON.stringify(json.errors)));
          else resolve(json);
        } catch (e) {
          reject(e);
        }
      });
    });
    req.on('error', reject);
    req.write(JSON.stringify({ query }));
    req.end();
  });
}

async function listPending(token) {
  const orgR = await queryBuffer(token, `query {
    account {
      organizations {
        id
      }
    }
  }`);
  const orgIds = orgR.data.account.organizations.map((org) => org.id);
  const out = [];
  for (const orgId of orgIds) {
    const postsR = await queryBuffer(token, `query {
      posts(input: {
        organizationId: "${orgId}",
        sort: [{ field: dueAt, direction: asc }],
        filter: { status: [scheduled] }
      }) {
        edges {
          node {
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
      }
    }`);
    for (const edge of postsR.data.posts.edges) {
        const post = edge.node;
        out.push({
          postId: post.id,
          channelId: post.channel.id,
          channelName: post.channel.name,
          service: post.channel.service,
          dueAt: post.dueAt,
          text: (post.text || '').slice(0, 80),
        });
    }
  }
  return out;
}

async function deletePost(token, postId) {
  const r = await queryBuffer(token, `mutation {
    deletePost(input: {id: "${postId}"}) {
      ... on PostActionSuccess { success }
      ... on MutationError { message }
    }
  }`);
  const result = r.data.deletePost;
  return result.success ? { ok: true } : { ok: false, error: result.message };
}

async function main() {
  const matchedByToken = [];
  for (const token of TOKENS) {
    try {
      const pending = await listPending(token);
      const posts = pending.filter((p) => p.dueAt >= FROM_UTC && p.dueAt < TO_UTC);
      matchedByToken.push({ token, posts });
    } catch (e) {
      console.error('查询失败:', e.message);
    }
  }

  const matched = matchedByToken.flatMap((m) => m.posts);
  console.log(`匹配队列 ${matched.length} 条（${FROM_UTC} ~ ${TO_UTC}），dry_run=${DRY_RUN}`);
  for (const p of matched) {
    console.log(`  [${p.service}] ${p.channelName} | ${p.dueAt} | ${p.postId} | ${p.text}`);
  }

  if (DRY_RUN) {
    console.log('dry-run，未删除任何帖子');
    return;
  }

  let ok = 0;
  let fail = 0;
  for (const { token, posts } of matchedByToken) {
    for (const p of posts) {
      const result = await deletePost(token, p.postId);
      if (result.ok) {
        ok++;
        console.log(`  已删除 ${p.postId}`);
      } else {
        fail++;
        console.error(`  删除失败 ${p.postId}: ${result.error}`);
      }
    }
  }
  console.log(`删除完成: 成功 ${ok}, 失败 ${fail}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
