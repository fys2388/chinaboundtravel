#!/usr/bin/env python3
import requests

WORKER_URL = "https://buffer-auto-poster.fys2388.workers.dev/publish"

test_payload = {
    "title": "Test Post",
    "desc": "This is a test description",
    "cover": "https://image.pollinations.ai/prompt/test%20image",
    "url": "https://chinaboundtravel.com/test"
}

print(f"测试 Worker: {WORKER_URL}")
print(f"Payload: {test_payload}")
print("-" * 50)

try:
    resp = requests.post(WORKER_URL, json=test_payload, timeout=90)
    print(f"HTTP Status: {resp.status_code}")
    print(f"Response: {resp.text}")
except Exception as e:
    print(f"Error: {str(e)}")
