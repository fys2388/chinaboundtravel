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
  console.log('=== Buffer API direct query for Pinterest channels ===\n');
  try {
    const r = await queryBuffer(`query {
      account {
        organizations {
          id
          name
          channels {
            id
            name
            service
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
