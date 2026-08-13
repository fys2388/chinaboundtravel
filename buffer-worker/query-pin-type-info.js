const https = require('https');
const PINTEREST_TOKEN = process.env.BUFFER_TOKEN_PINTEREST || process.env.BUFFER_TOKEN_PIN || 'BUFFER_TEST_TOKEN';

function queryBuffer(query, variables) {
  return new Promise((resolve, reject) => {
    const options = { hostname: 'api.buffer.com', port: 443, path: '/', method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + PINTEREST_TOKEN } };
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => { try { resolve(JSON.parse(data)); } catch (e) { reject(e); } });
    });
    req.on('error', reject);
    const body = { query };
    if (variables) body.variables = variables;
    req.write(JSON.stringify(body));
    req.end();
  });
}

async function main() {
  // 查询 PinterestMetadata 的完整字段结构，看有没有默认board
  console.log('=== Query 1: PinterestMetadata all fields ===');
  try {
    const r1 = await queryBuffer('query { __type(name: "PinterestMetadata") { name fields { name type { name kind ofType { name } } } } }');
    console.log(JSON.stringify(r1, null, 2));
  } catch (e) { console.error('Error:', e.message); }

  // 查询 PinterestMetadataInput 的字段
  console.log('\n=== Query 2: PinterestMetadataInput ===');
  try {
    const r2 = await queryBuffer('query { __type(name: "PinterestPostMetadataInput") { name inputFields { name type { name kind ofType { name } } defaultValue } } }');
    console.log(JSON.stringify(r2, null, 2));
  } catch (e) { console.error('Error:', e.message); }

  // 检查完整的 channel metadata
  console.log('\n=== Query 3: Full channel metadata ===');
  try {
    const r3 = await queryBuffer('query { account { organizations { channels { id name service metadata { ... on PinterestMetadata { __typename } } } } } }');
    console.log(JSON.stringify(r3, null, 2));
  } catch (e) { console.error('Error:', e.message); }
}

main();
