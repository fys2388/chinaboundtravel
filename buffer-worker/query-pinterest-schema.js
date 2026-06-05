const https = require('https');

const BUFFER_TOKEN = '***REMOVED***';

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
  // 1. 查所有含 "pinterest" 的类型
  console.log('=== Types with "pinterest" ===\n');
  const r1 = await queryBuffer('query { __schema { types { name fields { name type { name kind ofType { name } } } } } }');
  const types = r1.data.__schema.types;
  for (const t of types) {
    if (!t.name) continue;
    const lower = t.name.toLowerCase();
    if (lower.includes('pinterest') || lower.includes('board')) {
      console.log(`\n--- ${t.name} ---`);
      if (t.fields) {
        for (const f of t.fields) {
          if (!f) continue;
          console.log(`  ${f.name}: ${f.type?.name || f.type?.ofType?.name || f.type?.kind}`);
        }
      }
    }
  }

  // 2. 查 Channel 的 subTypes (union)
  console.log('\n=== Channel / ChannelMetadata possible unions ===\n');
  for (const t of types) {
    if (!t.name) continue;
    if (t.name === 'Channel' || t.name === 'ChannelMetadata' || t.name === 'PinterestChannel' || t.name === 'PostMetadata') {
      console.log(`\n--- ${t.name} (${t.kind}) ---`);
      if (t.fields) {
        for (const f of t.fields) {
          if (!f) continue;
          let desc = '';
          if (f.type?.kind === 'NON_NULL') desc = f.type.ofType?.name + '!';
          else if (f.type?.kind === 'LIST') desc = '[' + (f.type.ofType?.ofType?.name || f.type.ofType?.name) + ']';
          else desc = f.type?.name || f.type?.kind;
          console.log(`  ${f.name}: ${desc}`);
        }
      }
      if (t.possibleTypes) {
        console.log('  possibleTypes:');
        for (const pt of t.possibleTypes) {
          console.log(`    - ${pt.name}`);
        }
      }
    }
  }
}

main();
