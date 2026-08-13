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
  console.log('=== Query: organization.channels (simple) ===');
  try {
    const r = await queryBuffer(`query {
      organization(id: "6a20329943b37a7289e25b6d") {
        id
        name
        channels {
          id
          name
          service
          isDisconnected
          isLocked
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
    console.log(JSON.stringify(r, null, 2));
  } catch (e) { console.error('Error:', e.message); }
}

main();
