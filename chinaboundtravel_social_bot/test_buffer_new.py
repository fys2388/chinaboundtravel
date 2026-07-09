import requests
import json

API_TOKEN = "***REMOVED***"
BASE_URL = "https://api.buffer.com"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

def test_organizations():
    print("=== Step 1: Get Organizations ===")
    query = """
    query GetOrganizations {
        account {
            organizations {
                id
                name
            }
        }
    }
    """
    response = requests.post(BASE_URL, json={"query": query}, headers=headers)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Result: {json.dumps(result, indent=2)}")
    return result

def test_channels(org_id):
    print("\n=== Step 2: Get Channels ===")
    query = """
    query GetChannels($orgId: String!) {
        organization(id: $orgId) {
            id
            name
            channels {
                id
                service
                name
            }
        }
    }
    """
    variables = {"orgId": org_id}
    response = requests.post(BASE_URL, json={"query": query, "variables": variables}, headers=headers)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Result: {json.dumps(result, indent=2)}")
    return result

def test_create_post(channel_id):
    print("\n=== Step 3: Create Post ===")
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
    return result

def test_channels_direct():
    print("\n=== Step 2b: Get Channels Direct ===")
    query = """
    query GetChannelsDirect {
        account {
            organizations {
                id
                name
            }
        }
    }
    """
    response = requests.post(BASE_URL, json={"query": query}, headers=headers)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Result: {json.dumps(result, indent=2)}")
    return result

def test_post_direct():
    print("\n=== Step 3: Test Create Post Direct ===")
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
            "channelId": "6a17e044c687a22dd4346bf4",
            "text": "Test post from ChinaBound Travel API! https://chinaboundtravel.com #ChinaTravel",
            "schedulingType": "automatic",
            "mode": "shareNow"
        }
    }
    response = requests.post(BASE_URL, json={"query": query, "variables": variables}, headers=headers)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Result: {json.dumps(result, indent=2)}")
    return result

if __name__ == "__main__":
    org_result = test_organizations()
    
    org_id = org_result.get("data", {}).get("account", {}).get("organizations", [{}])[0].get("id")
    
    if org_id:
        channels_result = test_channels(org_id)
        
        org_data = channels_result.get("data", {}).get("organization")
        if org_data:
            channels = org_data.get("channels", [])
            if channels:
                channel_id = channels[0]["id"]
                print(f"\nFound channels: {channels}")
                test_create_post(channel_id)
            else:
                print("\nNo channels found")
        else:
            print("\nOrganization data is null, trying direct post...")
            test_post_direct()
    else:
        print("\nNo organization found")