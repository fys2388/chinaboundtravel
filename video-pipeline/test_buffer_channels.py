import requests

API_TOKEN = "***REMOVED***"
headers = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}

org_id = "6a20329943b37a7289e25b6d"

query = """
query GetChannels($orgId: String!) {
    organization(id: $orgId) {
        channels {
            id
            service
            name
        }
    }
}
"""

response = requests.post("https://api.buffer.com", json={"query": query, "variables": {"orgId": org_id}}, headers=headers)
print(f"Status: {response.status_code}")
print(f"Result: {response.text}")
