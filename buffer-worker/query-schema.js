const https = require('https');

const BUFFER_TOKEN = process.env.BUFFER_TOKEN || 'BUFFER_TEST_TOKEN';

function queryBuffer(query) {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'api.buffer.com',
      port: 443,
      path: '/',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${BUFFER_TOKEN}`
      }
    };

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          console.error('Parse error:', data.substring(0, 500));
          reject(e);
        }
      });
    });

    req.on('error', reject);
    req.write(JSON.stringify({ query }));
    req.end();
  });
}

async function main() {
  // 1. Find CreatePostInput type
  console.log('=== Querying CreatePostInput schema ===');
  try {
    const r1 = await queryBuffer('query { __type(name: "CreatePostInput") { name fields { name type { name kind ofType { name kind ofType { name kind ofType { name } } } } } } }');
    console.log(JSON.stringify(r1, null, 2));
  } catch (e) { console.error(e.message); }

  // 2. Find all types with "type" field
  console.log('\n=== Searching for post/facebook/instagram/channel types ===');
  try {
    const r2 = await queryBuffer('query { __schema { types { name fields { name type { name kind ofType { name kind ofType { name } } } } } } }');
    const types = r2.data.__schema.types;
    const keywords = ['post', 'facebook', 'instagram', 'channel', 'media', 'asset', 'input'];
    
    for (const t of types) {
      if (!t.name || !t.fields) continue;
      const nameLower = t.name.toLowerCase();
      if (!keywords.some(k => nameLower.includes(k))) continue;
      
      console.log(`\n--- ${t.name} ---`);
      for (const f of t.fields) {
        if (!f) continue;
        let desc = '';
        let ft = f.type;
        if (ft.kind === 'NON_NULL') {
          ft = ft.ofType;
          desc = '!';
        }
        if (ft.kind === 'LIST') {
          desc = `[${ft.ofType?.name || ''}]${desc}`;
        } else {
          desc = `${ft.name || ''}${desc}`;
        }
        console.log(`  ${f.name}: ${desc}`);
      }
    }

    console.log('\n=== Types with field named "type" ===');
    for (const t of types) {
      if (!t.name || !t.fields) continue;
      for (const f of t.fields) {
        if (f && f.name === 'type') {
          let desc = '';
          let ft = f.type;
          if (ft.kind === 'NON_NULL') {
            ft = ft.ofType;
            desc = '!';
          }
          desc = `${ft.name || ''}${desc}`;
          console.log(`  ${t.name}.type: ${desc}`);
        }
      }
    }
  } catch (e) { console.error(e.message); }
}

main();
