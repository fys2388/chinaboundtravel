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

function getTypeDesc(t) {
  if (!t) return '';
  if (t.kind === 'NON_NULL') {
    return `${getTypeDesc(t.ofType)}!`;
  }
  if (t.kind === 'LIST') {
    return `[${getTypeDesc(t.ofType)}]`;
  }
  return t.name || t.kind;
}

async function main() {
  // Get all input types
  console.log('=== Searching for specific types ===\n');
  const r = await queryBuffer('query { __schema { types { name kind fields { name type { name kind ofType { name kind ofType { name kind ofType { name } } } } } inputFields { name type { name kind ofType { name kind ofType { name kind ofType { name } } } } } } } }');
  const types = r.data.__schema.types;
  
  // Search for: CreatePostInput, PostMetadata, FacebookPostMetadata, InstagramPostMetadata, CommonPostMetadata, Asset, ImageAsset
  const targetNames = ['CreatePostInput', 'PostMetadata', 'FacebookPostMetadata', 'InstagramPostMetadata', 'CommonPostMetadata', 'TwitterPostMetadata', 'PinterestPostMetadata', 'Asset', 'ImageAsset', 'MediaAsset', 'Annotation', 'AssetInput', 'PostAssetInput'];

  for (const targetName of targetNames) {
    const t = types.find(x => x.name === targetName);
    if (!t) {
      console.log(`❌ ${targetName} NOT FOUND`);
      continue;
    }
    console.log(`\n=== ${targetName} (kind: ${t.kind}) ===`);
    
    const fields = t.fields || t.inputFields;
    if (!fields || fields.length === 0) {
      console.log('  (no fields)');
      continue;
    }
    
    for (const f of fields) {
      if (!f) continue;
      console.log(`  ${f.name}: ${getTypeDesc(f.type)}`);
    }
  }

  // Also search for ANY input types with "post" in name
  console.log('\n=== ALL Input types with post/facebook/instagram/asset ===\n');
  for (const t of types) {
    if (t.kind !== 'INPUT_OBJECT' || !t.name) continue;
    const lower = t.name.toLowerCase();
    if (!lower.includes('post') && !lower.includes('facebook') && !lower.includes('instagram') && !lower.includes('asset') && !lower.includes('media')) continue;
    
    console.log(`\n--- ${t.name} ---`);
    const fields = t.inputFields || t.fields || [];
    for (const f of fields) {
      if (!f) continue;
      console.log(`  ${f.name}: ${getTypeDesc(f.type)}`);
    }
  }
}

main();
