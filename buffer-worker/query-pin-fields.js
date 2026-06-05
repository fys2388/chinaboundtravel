const https = require('https');
const BUFFER_TOKEN = '***REMOVED***';

function queryBuffer(query, variables) {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'api.buffer.com', port: 443, path: '/', method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + BUFFER_TOKEN }
    };
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
  // 查 PinterestPostMetadataInput 完整字段
  const r1 = await queryBuffer('query { __schema { types(kind: INPUT_OBJECT) { name inputFields { name type { name kind ofType { name kind ofType { name } } } } }');
  const types = r1.data.__schema.types;
  console.log('=== PinterestPostMetadataInput ===');
  for (const t of types) {
    if (t.name === 'PinterestPostMetadataInput') {
      for (const f of t.inputFields || []) {
        let tn = f.type;
        let desc = '';
        if (tn.kind === 'NON_NULL') desc = tn.ofType.name + '!';
        else if (tn.kind === 'LIST') desc = '[' + (tn.ofType.name + ']';
        else desc = tn.name || tn.kind;
        console.log('  ' + f.name + ': ' + desc);
      }
    }
  }

  // 测试发布 Pinterest
  const mutation = 'mutation CreatePost($input: CreatePostInput!) { createPost(input: $input) { ... on PostActionSuccess { post { id channel { service } } } ... on MutationError { message } } }';
  const variables = {
    input: {
      text: 'China Travel Tips: Exploring China Bound Travel blog about China travel. #ChinaTravel',
      channelId: '6a219362c687a22dd45dd1d5',
      schedulingType: 'automatic',
      mode: 'addToQueue',
      assets: [{ image: { url: 'https://images.unsplash.com/photo-1513407030348-c983a97b98d8?q=80&w=1080&auto=format&fit=crop' }]
    }
  };

  console.log('\n=== 测试无 metadata.pinterest.boardServiceId 发布 ===');
  try {
    const r2 = await queryBuffer(mutation, variables);
    console.log(JSON.stringify(r2, null, 2).substring(0, 2000);
  } catch (e) {
    console.error(e.message);
  }
}

main();
