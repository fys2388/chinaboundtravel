const https = require('https');
const PINTEREST_TOKEN = '***REMOVED***';

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
  // 查询 Mutation 中所有与 Pinterest/board 相关的字段
  console.log('=== Searching Mutation for board/pinterest ===');
  try {
    const r = await queryBuffer('query { __type(name: "Mutation") { name fields { name args { name type { name } } } } }');
    const fields = r.data?.__type?.fields || [];
    for (const f of fields) {
      const name = f.name.toLowerCase();
      if (name.includes('board') || name.includes('pin') || name.includes('pinterest')) {
        console.log(`  ${f.name}: args=${JSON.stringify(f.args?.map(a => a.name + ':' + a.type.name))}`);
      }
    }
    console.log(`\nTotal mutations: ${fields.length}`);
    // 打印前20个
    console.log('\nSample mutation names:');
    for (let i = 0; i < Math.min(20, fields.length); i++) {
      console.log(`  ${fields[i].name}`);
    }
  } catch (e) { console.error('Error:', e.message); }
}

main();
