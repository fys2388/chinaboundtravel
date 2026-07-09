import requests
import os

API_TOKEN = "***REMOVED***"
headers = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}

print("=== Test 1: Upload File ===")
video_path = r"e:\AI\dulizhan\travel-blog\video-pipeline\output\973773db.mp4"

upload_url = "https://api.buffer.com/1/upload.json"
upload_headers = {"Authorization": f"Bearer {API_TOKEN}"}

if os.path.exists(video_path):
    print(f"File exists: {os.path.getsize(video_path)} bytes")
    with open(video_path, "rb") as f:
        files = {"file": (os.path.basename(video_path), f, "video/mp4")}
        response = requests.post(upload_url, headers=upload_headers, files=files, timeout=60)
    print(f"Upload status: {response.status_code}")
    print(f"Upload result: {response.text[:500]}")
else:
    print("File not found")

print("\n=== Test 2: Create Text Post ===")
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
