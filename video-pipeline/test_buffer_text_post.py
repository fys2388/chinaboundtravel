import os
import requests

API_TOKEN = os.environ.get("BUFFER_ACCESS_TOKEN", "BUFFER_TEST_TOKEN")
headers = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}

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

response = requests.post("https://api.buffer.com", json={"query": query, "variables": variables}, headers=headers)
print(f"Create post status: {response.status_code}")
print(f"Create post result: {response.text}")
