const https = require('https');

const BUFFER_TOKEN = process.env.BUFFER_TOKEN || 'BUFFER_TEST_TOKEN';
const PINTEREST_TOKEN = process.env.BUFFER_TOKEN_PINTEREST || process.env.BUFFER_TOKEN_PIN || 'BUFFER_TEST_TOKEN';

function queryBuffer(query, variables, token) {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'api.buffer.com',
      port: 443,
      path: '/',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
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
    req.write(JSON.stringify({ query, variables }));
    req.end();
  });
}

const MUTATION = `mutation CreatePost($input: CreatePostInput!) {
  createPost(input: $input) {
    ... on PostActionSuccess {
      post {
        id
        channel {
          id
          service
          name
        }
      }
    }
    ... on MutationError {
      message
    }
  }
}`;

async function testFacebook() {
  console.log('=== Testing Facebook Post ===\n');
  const variables = {
    input: {
      text: 'Test post for China Travel! #ChinaTravel #VisitChina',
      channelId: '6a17e0c4c687a22dd4346d3c',
      schedulingType: 'automatic',
      mode: 'addToQueue',
      assets: [],
      metadata: {
        facebook: {
          type: 'post'
        }
      }
    }
  };

  const result = await queryBuffer(MUTATION, variables, BUFFER_TOKEN);
  console.log(JSON.stringify(result, null, 2));
}

async function testInstagram() {
  console.log('\n=== Testing Instagram Post ===\n');
  const variables = {
    input: {
      text: 'Beautiful China! #ChinaTravel #Travel',
      channelId: '6a17e14dc687a22dd4346eb4',
      schedulingType: 'automatic',
      mode: 'addToQueue',
      assets: [{
        image: {
          url: 'https://images.unsplash.com/photo-1513407030348-c983a97b98d8?q=80&w=1080&auto=format&fit=crop'
        }
      }],
      metadata: {
        instagram: {
          type: 'post',
          shouldShareToFeed: true
        }
      }
    }
  };

  const result = await queryBuffer(MUTATION, variables, BUFFER_TOKEN);
  console.log(JSON.stringify(result, null, 2));
}

async function testTwitter() {
  console.log('\n=== Testing Twitter Post (as reference - should work) ===\n');
  const variables = {
    input: {
      text: 'Test China travel tweet! #ChinaTravel',
      channelId: '6a202882c687a22dd45735b6',
      schedulingType: 'automatic',
      mode: 'addToQueue',
      assets: []
    }
  };

  const result = await queryBuffer(MUTATION, variables, BUFFER_TOKEN);
  console.log(JSON.stringify(result, null, 2));
}

async function main() {
  try {
    await testFacebook();
    await testInstagram();
    await testTwitter();
  } catch (e) {
    console.error('Error:', e.message);
  }
}

main();
