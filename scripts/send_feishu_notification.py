#!/usr/bin/env python3
"""Send a Feishu group notification via webhook (with signature).

Usage:
  python scripts/send_feishu_notification.py --text "message"
  Env: FEISHU_WEBHOOK_URL, FEISHU_SECRET (optional; skips if webhook unset)
"""
import argparse
import base64
import hashlib
import hmac
import os
import sys
import time

import requests


def sign(timestamp: str, secret: str) -> str:
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(hmac_code).decode("utf-8")


def send(webhook: str, secret: str, text: str):
    ts = str(int(time.time()))
    payload = {
        "timestamp": ts,
        "sign": sign(ts, secret),
        "msg_type": "text",
        "content": {"text": text},
    }
    resp = requests.post(webhook, json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="Send Feishu webhook notification")
    parser.add_argument("--text", default="", help="Message text to send")
    parser.add_argument(
        "--webhook", default=os.environ.get("FEISHU_WEBHOOK_URL", "")
    )
    parser.add_argument(
        "--secret", default=os.environ.get("FEISHU_SECRET", "")
    )
    args = parser.parse_args()

    if not args.webhook:
        print("FEISHU_WEBHOOK_URL not set, skip notification", file=sys.stderr)
        return 0
    result = send(args.webhook, args.secret, args.text)
    print("Feishu notification sent:", result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
