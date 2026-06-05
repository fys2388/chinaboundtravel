const https = require('https');
const BUFFER_TOKEN = process.env.BUFFER_TOKEN || '';
const PINTEREST_TOKEN = process.env.BUFFER_TOKEN_PINTEREST || process.env.BUFFER_TOKEN_PIN || '';

function queryBuffer(query, token) {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'api.buffer.com', port: 443, path: '/', method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token }
    };
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
  // 先用主账户查
  console.log('=== Using BUFFER_TOKEN (main account) ===');
  try {
    const r1 = await queryBuffer(`query {
      account {
        organizations {
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
    }`, BUFFER_TOKEN);
    console.log(JSON.stringify(r1, null, 2));
  } catch (e) {
    console.error('Error with main token:', e.message);
  }

  // 用Pinterest账户查
  if (PINTEREST_TOKEN) {
    console.log('\n=== Using BUFFER_TOKEN_PINTEREST ===');
    try {
      const r2 = await queryBuffer(`query {
        account {
          organizations {
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
      }`, PINTEREST_TOKEN);
      console.log(JSON.stringify(r2, null, 2));
    } catch (e) {
      console.error('Error with pinterest token:', e.message);
    }
  } else {
    console.log('\nNo Pinterest token set. Set BUFFER_TOKEN_PINTEREST env var.');
  }
}

main();
