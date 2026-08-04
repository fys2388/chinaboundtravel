const https = require('https');
const http = require('http');
const { URL } = require('url');

const URLS = [
  { name: 'esim (Airalo)', url: 'https://www.airalo.com/promo/38j3e4' },
  { name: 'vpn (affiliatescn)', url: 'https://get.affiliatescn.net/aff_c?offer_id=153&aff_id=150687&url_id=613' },
  { name: 'vpnNord (affiliatescn)', url: 'https://get.affiliatescn.net/aff_c?offer_id=153&aff_id=150687&url_id=613' },
  { name: 'nordpass', url: 'https://go.nordpass.io/off/?offer_id=488&aff_id=150687&url_id=9356' },
  { name: 'hotel (Booking.com)', url: 'https://www.booking.com/index.html?aid=730795' },
  { name: 'klook', url: 'https://klook.tpo.li/vrPkmS2v' },
  { name: 'safetywing', url: 'https://safetywing.com/nomad-insurance?referenceID=26548976&utm_source=26548976&utm_medium=Ambassador' },
  { name: 'trip (trains)', url: 'https://trip.tpo.li/trains?marker=730795' },
  { name: 'flight (aviasales)', url: 'https://aviasales.travelpayouts.com/search?marker=730795' },
  { name: 'worldnomads', url: 'https://safetywing.com/nomad-insurance?referenceID=26548976&utm_source=26548976&utm_medium=Ambassador' },
  { name: 'allianz', url: 'https://safetywing.com/nomad-insurance?referenceID=26548976&utm_source=26548976&utm_medium=Ambassador' },
];

function checkUrl(url, method = 'HEAD', insecure = false) {
  return new Promise((resolve) => {
    const parsed = new URL(url);
    const client = parsed.protocol === 'https:' ? https : http;
    const options = { method, timeout: 20000 };
    if (insecure) options.rejectUnauthorized = false;
    const req = client.request(parsed, options, (res) => {
      const status = res.statusCode;
      if (status >= 300 && status < 400 && res.headers.location) {
        const redirectUrl = new URL(res.headers.location, url).toString();
        checkUrl(redirectUrl, method, insecure).then(r => resolve({ ...r, originalUrl: url }));
        return;
      }
      if (status === 405 && method === 'HEAD') {
        checkUrl(url, 'GET', insecure).then(r => resolve({ ...r, originalUrl: url }));
        return;
      }
      if (method === 'GET') res.resume();
      resolve({ url, status, ok: status >= 200 && status < 400, method });
    });
    req.on('error', (err) => {
      if (!insecure && err.message.includes('certificate')) {
        checkUrl(url, method, true).then(r => resolve({ ...r, originalUrl: url, note: 'used insecure mode due to cert' }));
      } else {
        resolve({ url, status: 'ERROR', ok: false, error: err.message });
      }
    });
    req.on('timeout', () => { req.destroy(); resolve({ url, status: 'TIMEOUT', ok: false }); });
    req.end();
  });
}

async function main() {
  console.log(`Checking ${URLS.length} affiliate URLs from hugo.toml...\n`);
  for (const item of URLS) {
    let r = await checkUrl(item.url, 'HEAD');
    if (!r.ok && r.status !== 'TIMEOUT' && r.status !== 'ERROR') {
      const getR = await checkUrl(item.url, 'GET');
      if (getR.ok) r = getR;
    }
    const status = r.ok ? 'OK' : 'FAIL';
    console.log(`[${status}] ${item.name}`);
    console.log(`       URL: ${r.originalUrl || r.url}`);
    console.log(`       Status: ${r.status}${r.method ? ' (' + r.method + ')' : ''}${r.note ? ' | ' + r.note : ''}${r.error ? ' | Error: ' + r.error : ''}`);
    if (r.url !== r.originalUrl && r.originalUrl) {
      console.log(`       Final URL: ${r.url}`);
    }
    console.log();
  }
}

main();
