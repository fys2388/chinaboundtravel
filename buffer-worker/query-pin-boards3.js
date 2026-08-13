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
  const q = `query {
    account {
      organizations {
        channels {
          id
          name
          service
          metadata {
            __typename
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
  }`;

  const r = await queryBuffer(q);
  console.log(JSON.stringify(r, null, 2).substring(0, 5000));
}

main();
