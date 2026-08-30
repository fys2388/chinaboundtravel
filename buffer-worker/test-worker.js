const https = require('https');

const WORKER_URL = 'https://buffer-worker.chinaboundtravel.com';

function postToWorker(body) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const url = new URL(WORKER_URL + '/publish');
    const options = {
      hostname: url.hostname,
      port: 443,
      path: url.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(data)
      }
    };

    const req = https.request(options, (res) => {
      let resp = '';
      res.on('data', (chunk) => { resp += chunk; });
      res.on('end', () => {
        try {
          resolve(JSON.parse(resp));
        } catch (e) {
          console.error('Parse error:', resp.substring(0, 500));
          reject(e);
        }
      });
    });

    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

async function testPublish() {
  console.log('=== Testing Worker /publish endpoint ===\n');
  
  const body = {
    title: 'China Travel Guide - Top 5 Must-Visit Places',
    desc: 'Discover the breathtaking beauty of China! From the majestic Great Wall to the mystical Zhangjiajie mountains, explore the top destinations for your next adventure. #ChinaTravel #VisitChina #AsiaTravel',
    cover: 'https://images.unsplash.com/photo-1513407030348-c983a97b98d8?q=80&w=1080&auto=format&fit=crop',
    url: 'https://chinaboundtravel.com'
  };

  console.log('Request body:', JSON.stringify(body, null, 2));
  console.log('');
  
  const result = await postToWorker(body);
  console.log('Response:', JSON.stringify(result, null, 2));
}

testPublish().catch(e => console.error('Error:', e));
