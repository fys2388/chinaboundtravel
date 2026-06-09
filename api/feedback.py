#!/usr/bin/env python3
"""
用户反馈API端点
处理来自博客文章底部的用户反馈表单
"""

import os
import json
from datetime import datetime
from pathlib import Path

CONFIG_DIR = Path(__file__).parent.parent / "config"
FEEDBACK_FILE = CONFIG_DIR / "user_feedback.json"

def handler(event, context):
    """处理反馈请求"""
    try:
        # 解析请求体
        body = json.loads(event.get("body", "{}"))
        
        rating = body.get("rating")
        content = body.get("content", "")
        url = body.get("url", "")
        title = body.get("title", "")
        
        # 加载现有反馈
        if FEEDBACK_FILE.exists():
            with open(FEEDBACK_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {"feedbacks": [], "updated_at": None}
        
        # 添加新反馈
        feedback = {
            "id": f"fb_{int(datetime.now().timestamp())}",
            "rating": rating,
            "content": content,
            "url": url,
            "title": title,
            "timestamp": datetime.now().isoformat()
        }
        
        data["feedbacks"].append(feedback)
        data["updated_at"] = datetime.now().isoformat()
        
        # 保存反馈
        with open(FEEDBACK_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"success": True, "message": "Feedback saved successfully"})
        }
    
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"success": False, "error": str(e)})
        }


# 本地测试入口
if __name__ == "__main__":
    import sys
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import urllib.parse
    
    class FeedbackHandler(BaseHTTPRequestHandler):
        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
        
        def do_POST(self):
            if self.path == '/api/feedback':
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode('utf-8')
                
                event = {"body": body}
                result = handler(event, None)
                
                self.send_response(result["statusCode"])
                for key, value in result["headers"].items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(result["body"].encode('utf-8'))
        
        def log_message(self, format, *args):
            pass  # 禁用日志
    
    server = HTTPServer(('localhost', 8765), FeedbackHandler)
    print("Feedback API server running on http://localhost:8765/api/feedback")
    server.serve_forever()