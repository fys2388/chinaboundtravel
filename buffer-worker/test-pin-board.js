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
  // 测试：PinterestPostMetadataInput 的完整字段（简化查）
  console.log('=== 测试1: 不指定 boardServiceId ===');
  let mut = 'mutation CreatePost($input: CreatePostInput!) { createPost(input: $input) { ... on PostActionSuccess { post { id } } ... on MutationError { message } } }';
  let vars = { input: {
    text: 'China Travel - Discover amazing places to visit in China! #China #Travel',
    channelId: '6a21bdbec687a22dd45ec2ae',
    schedulingType: 'automatic',
    mode: 'addToQueue',
    metadata: { pinterest: { title: 'China Travel Guide' } },
    assets: [{ image: { url: 'https://images.unsplash.com/photo-1513407030348-c983a97b98d8?q=80&w=1080&auto=format&fit=crop' } }]
  }};
  console.log(JSON.stringify(vars, null, 2));
  let r = await queryBuffer(mut, vars);
  console.log('Result:', JSON.stringify(r, null, 2).substring(0, 1500));
  
  // 测试2: 给一个空 boardServiceId
  console.log('\n=== 测试2: metadata.pinterest 里补 boardServiceId ===');
  vars.input.metadata.pinterest.boardServiceId = '';
  r = await queryBuffer(mut, vars);
  console.log('Result:', JSON.stringify(r, null, 2).substring(0, 1500));
}

main();
