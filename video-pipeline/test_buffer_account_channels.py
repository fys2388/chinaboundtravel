import os
import requests

API_TOKEN = os.environ.get("BUFFER_ACCESS_TOKEN", "BUFFER_TEST_TOKEN")
headers = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}

query = """
query GetAccount {
    account {
        channels {
            id
            service
            name
        }
    }
}
"""

response = requests.post("https://api.buffer.com", json={"query": query}, headers=headers)
print(f"Status: {response.status_code}")
print(f"Result: {response.text}")
