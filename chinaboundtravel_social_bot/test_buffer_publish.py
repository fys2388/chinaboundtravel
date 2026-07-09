import requests
import json

API_TOKEN = "***REMOVED***"
BASE_URL = "https://api.buffer.com"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

channels = {
    "pinterest": "6a21bdbec687a22dd45ec2ae",
    "youtube": "6a48cfec5ab6d2f106a2b9fe",
    "tiktok": "6a48cf985ab6d2f106a2b8b8"
}

def test_post_to_channel(channel_name, channel_id):
    print(f"\n=== Posting to {channel_name} ({channel_id}) ===")
    
    query = """
    mutation CreatePost($input: CreatePostInput!) {
        createPost(input: $input) {
            ... on PostActionSuccess {
                post {
                    id
                    text
                }
            }
            ... on MutationError {
                message
            }
        }
    }
    """
    
    variables = {
        "input": {
            "channelId": channel_id,
            "text": "Test post from ChinaBound Travel API! https://chinaboundtravel.com #ChinaTravel",
            "schedulingType": "automatic",
            "mode": "shareNow"
        }
    }
    
    response = requests.post(BASE_URL, json={"query": query, "variables": variables}, headers=headers)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Result: {json.dumps(result, indent=2)}")
    
    if "errors" in result:
        return False
    
    create_post = result.get("data", {}).get("createPost", {})
    if "message" in create_post:
        print(f"Error message: {create_post['message']}")
        return False
    
    if "post" in create_post:
        print(f"✅ Success! Post ID: {create_post['post']['id']}")
        return True
    
    return False

if __name__ == "__main__":
    print("=== Buffer API Publishing Test ===")
    
    success_count = 0
    fail_count = 0
    
    for name, channel_id in channels.items():
        success = test_post_to_channel(name, channel_id)
        if success:
            success_count += 1
        else:
            fail_count += 1
    
    print(f"\n=== Summary ===")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")