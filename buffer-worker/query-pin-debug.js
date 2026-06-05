const https = require('https');
const PINTEREST_TOKEN = '***REMOVED***';

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
  // 查询1: 用已知 channelId 查该 channel
  console.log('=== Query 1: query known channelId ===');
  try {
    const r1 = await queryBuffer(`query {
      organization(id: "6a20329943b37a7289e25b6d") {
        channels {
          id
          name
          service
          isDisconnected
          isLocked
          postingSchedule
          metadata {
            ... on PinterestMetadata {
              boards {
                id
                name
                serviceId
                url
              }
            }
          }
        }
      }
    }`);
    console.log(JSON.stringify(r1, null, 2));
  } catch (e) { console.error('Error:', e.message); }

  // 查询2: 用 channel query 查特定 ID
  console.log('\n=== Query 2: query specific channel ===');
  try {
    const r2 = await queryBuffer(`query {
      channel(id: "6a219362c687a22dd45dd1d5") {
        id
        name
        service
        isDisconnected
        metadata {
          ... on PinterestMetadata {
            boards {
              id
              name
              serviceId
              url
            }
          }
        }
      }
    }`);
    console.log(JSON.stringify(r2, null, 2));
  } catch (e) { console.error('Error:', e.message); }

  // 查询3: 检查当前账户状态
  console.log('\n=== Query 3: check account status ===');
  try {
    const r3 = await queryBuffer('query { account { id email createdAt organizations { id name channelsCount } } }');
    console.log(JSON.stringify(r3, null, 2));
  } catch (e) { console.error('Error:', e.message); }
}

main();
