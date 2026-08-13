const https = require('https');

const BUFFER_TOKEN = process.env.BUFFER_TOKEN || 'BUFFER_TEST_TOKEN';

function queryBuffer(query) {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'api.buffer.com', port: 443, path: '/', method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${BUFFER_TOKEN}` }
    };
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try { resolve(JSON.parse(data)); } catch (e) { reject(e); }
      });
    });
    req.on('error', reject);
    req.write(JSON.stringify({ query }));
    req.end();
  });
}

async function main() {
  // 1. 查所有 channel type
  console.log('=== Query 1: channels with metadata (尝试不同查询方式\n');
  
  const queries = [
    'query { account { organizations { channels { id name service metadata { ... on PinterestMetadata { boards { id name serviceId url } } } } }',
    'query { account { organizations { channels { id name service } } } }',
    'query { account { organizations { channels { __typename id name service } } } }'
  ];

  for (let i = 0; i < queries.length; i++) {
    console.log(`\n--- Query ${i + 1} ---`);
    try {
      const r = await queryBuffer(queries[i]);
      const s = JSON.stringify(r, null, 2);
      console.log(s.substring(0, 4000));
    } catch (e) {
      console.error('Error:', e.message);
    }
  }
}

main();
