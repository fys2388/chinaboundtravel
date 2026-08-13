const https = require('https');
const BUFFER_TOKEN = process.env.BUFFER_TOKEN || 'BUFFER_TEST_TOKEN';

function queryBuffer(query, variables) {
  return new Promise((resolve, reject) => {
    const options = { hostname: 'api.buffer.com', port: 443, path: '/', method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + BUFFER_TOKEN } };
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => { try { resolve(JSON.parse(data)); } catch (e) { reject(e); } });
    });
    req.on('error', reject);
    const body = { query }; if (variables) body.variables = variables;
    req.write(JSON.stringify(body)); req.end();
  });
}

async function main() {
  const ts = Date.now();
  const title = 'China Travel Guide ' + ts;
  const text = 'Discover hidden gems in China! Ultimate travel tips for your China adventure ' + ts + ' #ChinaTravel #ChinaBound #VisitChina';
  
  // 用全新内容测试
  let mut = 'mutation CreatePost($input: CreatePostInput!) { createPost(input: $input) { ... on PostActionSuccess { post { id dueAt channel { service name } } } ... on MutationError { message } } }';
  let vars = { input: {
    text: text,
    channelId: '6a219362c687a22dd45dd1d5',
    schedulingType: 'automatic',
    mode: 'addToQueue',
    metadata: { pinterest: { title: title, url: 'https://chinaboundtravel.com' } },
    assets: [{ image: { url: 'https://images.unsplash.com/photo-1513407030348-c983a97b98d8?q=80&w=1080&auto=format&fit=crop' } }]
  }};
  
  console.log('=== 测试: metadata.pinterest + title + url (无 boardServiceId) ===');
  let r = await queryBuffer(mut, vars);
  console.log('Result:', JSON.stringify(r, null, 2).substring(0, 2000));
}

main();
