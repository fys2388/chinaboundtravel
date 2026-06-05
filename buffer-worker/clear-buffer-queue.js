const https = require('https');
const BUFFER_TOKEN = '***REMOVED***';

function queryBuffer(query, variables) {
  return new Promise((resolve, reject) => {
    const options = { 
      hostname: 'api.buffer.com', 
      port: 443, 
      path: '/', 
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json', 
        'Authorization': 'Bearer ' + BUFFER_TOKEN 
      } 
    };
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => { 
        try { 
          const json = JSON.parse(data);
          if (json.errors) {
            reject(new Error(JSON.stringify(json.errors)));
          } else {
            resolve(json);
          }
        } catch (e) { 
          reject(e); 
        } 
      });
    });
    req.on('error', reject);
    const body = { query };
    if (variables) body.variables = variables;
    req.write(JSON.stringify(body));
    req.end();
  });
}

async function getPendingPosts() {
  console.log('=== 查询待发布帖子 ===');
  const r = await queryBuffer(`query {
    account {
      organizations {
        channels {
          id
          name
          service
          posts(status: PENDING) {
            id
            text
            dueAt
            channel {
              service
            }
          }
        }
      }
    }
  }`);
  
  let pendingPosts = [];
  r.data.account.organizations.forEach(org => {
    org.channels.forEach(ch => {
      ch.posts.forEach(post => {
        pendingPosts.push({
          postId: post.id,
          channelId: ch.id,
          channelName: ch.name,
          service: ch.service,
          dueAt: post.dueAt,
          text: post.text.slice(0, 50) + '...'
        });
      });
    });
  });
  
  console.log(`共发现 ${pendingPosts.length} 篇待发布帖子:`);
  pendingPosts.forEach((p, i) => {
    console.log(`${i+1}. [${p.service}] ${p.channelName} - ${p.dueAt} - ${p.text}`);
  });
  
  return pendingPosts;
}

async function deletePost(postId) {
  try {
    const r = await queryBuffer(`mutation {
      deletePost(input: {id: "${postId}"}) {
        ... on PostActionSuccess {
          success
        }
        ... on MutationError {
          message
        }
      }
    }`);
    if (r.data.deletePost.success) {
      return { success: true, postId };
    } else {
      return { success: false, postId, error: r.data.deletePost.message };
    }
  } catch (e) {
    return { success: false, postId, error: e.message };
  }
}

async function main() {
  try {
    const pendingPosts = await getPendingPosts();
    
    if (pendingPosts.length === 0) {
      console.log('队列已为空，无需清理');
      return;
    }
    
    console.log('\n=== 开始删除待发布帖子 ===');
    let successCount = 0;
    let failCount = 0;
    
    for (const post of pendingPosts) {
      console.log(`删除: ${post.postId} (${post.service})...`);
      const result = await deletePost(post.postId);
      if (result.success) {
        successCount++;
        console.log(`  ✅ 成功`);
      } else {
        failCount++;
        console.log(`  ❌ 失败: ${result.error}`);
      }
    }
    
    console.log(`\n=== 清理完成 ===`);
    console.log(`成功: ${successCount} 篇`);
    console.log(`失败: ${failCount} 篇`);
    
  } catch (e) {
    console.error('错误:', e.message);
  }
}

main();
