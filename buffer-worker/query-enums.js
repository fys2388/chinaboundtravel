const https = require('https');

const BUFFER_TOKEN = '***REMOVED***';

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
  const r = await queryBuffer('query { __schema { types { name kind enumValues { name } } } }');
  const types = r.data.__schema.types;

  const targetEnums = ['PostType', 'PostTypeFacebook', 'PostTypeInstagram', 'SchedulingType', 'ShareMode', 'AssetType', 'MediaType', 'PostTypeGoogleBusiness'];
  
  for (const name of targetEnums) {
    const t = types.find(x => x.name === name);
    if (!t) {
      console.log(`❌ ${name} NOT FOUND`);
      continue;
    }
    console.log(`\n=== ${name} (${t.kind}) ===`);
    if (t.enumValues && t.enumValues.length > 0) {
      for (const v of t.enumValues) {
        console.log(`  - ${v.name}`);
      }
    } else {
      console.log('  (no enum values)');
    }
  }

  // Also check all enum values containing "PostType"
  console.log('\n=== All enums with "PostType" or "Share" or "Scheduling" ===\n');
  for (const t of types) {
    if (t.kind !== 'ENUM' || !t.name) continue;
    const lower = t.name.toLowerCase();
    if (!lower.includes('posttype') && !lower.includes('share') && !lower.includes('scheduling') && !lower.includes('asset')) continue;
    console.log(`\n--- ${t.name} ---`);
    if (t.enumValues) {
      for (const v of t.enumValues) {
        console.log(`  - ${v.name}`);
      }
    }
  }
}

main();
