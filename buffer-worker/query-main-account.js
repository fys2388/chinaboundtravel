const https = require('https');
const BUFFER_TOKEN = '***REMOVED***';

function queryBuffer(query) {
  return new Promise((resolve, reject) => {
    const options = { hostname: 'api.buffer.com', port: 443, path: '/', method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + BUFFER_TOKEN } };
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
  console.log('=== Query: main account - check all channels including Pinterest ===\n');
  try {
    const r = await queryBuffer(`query {
      account {
        id
        email
        organizations {
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
      }
    }`);
    console.log(JSON.stringify(r, null, 2));
  } catch (e) { console.error('Error:', e.message); }
}

main();
