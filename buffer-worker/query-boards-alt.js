const https = require('https');

const PINTEREST_TOKEN = process.env.BUFFER_TOKEN_PINTEREST || process.env.BUFFER_TOKEN_PIN || 'BUFFER_TEST_TOKEN';

function queryBuffer(query) {
  return new Promise((resolve, reject) => {
    const options = { hostname: 'api.buffer.com', port: 443, path: '/', method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + PINTEREST_TOKEN } };
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => { try { resolve(JSON.parse(data)); } catch (e) { reject(e); } });
    });
    req.on('error', reject);
    req.write(JSON.stringify({ query }));
    req.end();
  });
}

async function main() {
  // 尝试多种查询方式找boards
  const queries = [
    // 方式1: 检查 channel metadata typename
    'query { account { organizations { channels { id name service metadata { __typename } } } } }',
    // 方式2: 更详细的 PinterestMetadata
    'query { account { organizations { channels { ... on PinterestChannel { id name metadata { boards { id name serviceId url } } } } } } }',
    // 方式3: 查询 posts 看是否能找到board
    'query { posts(first: 5) { edges { node { id service update { text } } } } }',
  ];

  for (let i = 0; i < queries.length; i++) {
    console.log(`\n=== Query ${i + 1} ===`);
    try {
      const r = await queryBuffer(queries[i]);
      const str = JSON.stringify(r, null, 2);
      console.log(str.substring(0, 3000));
    } catch (e) {
      console.error('Error:', e.message);
    }
  }
}

main();
