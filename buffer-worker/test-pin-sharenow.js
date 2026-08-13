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
  // 完全随机内容+图片
  const ts = Date.now();
  const randomText = 'Amazing Chinese architectural wonders - ' + ts + '. The Forbidden City, Temple of Heaven, and more iconic landmarks showcase thousands of years of Chinese history and culture. #China #Architecture #History #Travel';
  const randomImage = 'https://images.unsplash.com/photo-1508804185873-d9d2b4c61e51?q=80&w=1080&auto=format&fit=crop&sig=' + ts;
  
  const mut = 'mutation CreatePost($input: CreatePostInput!) { createPost(input: $input) { ... on PostActionSuccess { post { id dueAt channel { service name } } } ... on MutationError { message } } }';
  
  // 测试1: shareNow 模式 + 无 metadata（最简洁）
  console.log('=== 测试1: shareNow + 无 metadata.pinterest ===');
  let vars1 = { input: {
    text: randomText,
    channelId: '6a219362c687a22dd45dd1d5',
    schedulingType: 'automatic',
    mode: 'shareNow',
    assets: [{ image: { url: randomImage } }]
  }};
  let r = await queryBuffer(mut, vars1);
  console.log('Result1:', JSON.stringify(r, null, 2).substring(0, 1500));

  // 测试2: shareNow + metadata.pinterest.title + url
  console.log('\n=== 测试2: shareNow + metadata.pinterest.title + url ===');
  let vars2 = { input: {
    text: 'Explore the beauty of traditional Chinese gardens - ' + ts,
    channelId: '6a219362c687a22dd45dd1d5',
    schedulingType: 'automatic',
    mode: 'shareNow',
    metadata: { pinterest: { title: 'Chinese Gardens ' + ts, url: 'https://chinaboundtravel.com/china-gardens-' + ts } },
    assets: [{ image: { url: 'https://images.unsplash.com/photo-1519999482648-25049ddd37b1?q=80&w=1080&auto=format&fit=crop' } }]
  }};
  r = await queryBuffer(mut, vars2);
  console.log('Result2:', JSON.stringify(r, null, 2).substring(0, 1500));
}

main();
