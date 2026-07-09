import requests
import json

API_TOKEN = "***REMOVED***"
BASE_URL = "https://api.buffer.com"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

def test_channels_query():
    print("=== Test channels query ===")
    query = """
    query GetChannels($input: ChannelsInput!) {
        channels(input: $input) {
            id
            service
            name
        }
    }
    """
    variables = {"input": {"organizationId": "6a20329943b37a7289e25b6d"}}
    response = requests.post(BASE_URL, json={"query": query, "variables": variables}, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Result: {response.text}")

def test_channel_query():
    print("\n=== Test channel query ===")
    query = """
    query GetChannel($id: String!) {
        channel(id: $id) {
            id
            service
            name
        }
    }
    """
    variables = {"id": "6a17e044c687a22dd4346bf4"}
    response = requests.post(BASE_URL, json={"query": query, "variables": variables}, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Result: {response.text}")

if __name__ == "__main__":
    test_channels_query()
    test_channel_query()