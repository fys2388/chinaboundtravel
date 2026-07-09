import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import json
from dotenv import load_dotenv
from openai import OpenAI
import httpx

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

def test_doubao_api():
    print("=" * 60)
    print("豆包API测试")
    print("=" * 60)
    
    api_key = os.environ.get("DOUBAO_ARK_API_KEY", "")
    model = os.environ.get("DOUBAO_MODEL", "")
    base_url = "https://ark.cn-beijing.volces.com/api/v3"
    
    if not api_key:
        print("❌ DOUBAO_API_KEY 未配置")
        print("请在 .env 文件中设置 DOUBAO_API_KEY 和 DOUBAO_MODEL")
        print("\n配置步骤:")
        print("1. 访问 https://console.volcengine.com/ark/")
        print("2. 创建API Key")
        print("3. 创建推理接入点，获取 endpoint-id")
        print("4. 在.env中设置:")
        print("   DOUBAO_API_KEY=你的api-key")
        print("   DOUBAO_MODEL=你的endpoint-id (如 ep-xxx)")
        return False
    
    if not model:
        print("❌ DOUBAO_MODEL 未配置")
        print("请在 .env 文件中设置 DOUBAO_MODEL (推理接入点的endpoint-id)")
        return False
    
    print(f"API Key: {api_key[:8]}...")
    print(f"Model: {model}")
    print(f"Base URL: {base_url}")
    
    try:
        http_client = httpx.Client()
        client = OpenAI(api_key=api_key, base_url=base_url, http_client=http_client)
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello! What is your name?"}
            ],
            temperature=0.7
        )
        
        content = response.choices[0].message.content.strip()
        print(f"\n✅ API调用成功!")
        print(f"响应: {content}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ API调用失败: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_doubao_api()
    print("\n" + "=" * 60)
    print("测试" + ("通过" if success else "失败"))
    print("=" * 60)