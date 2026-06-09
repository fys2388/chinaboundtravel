import os
import requests
from tenacity import retry, stop_after_attempt, wait_exponential


class DoubaoArkClient:
    """豆包 Ark API 客户端"""
    
    def __init__(self):
        self.api_key = os.getenv("DOUBAO_ARK_API_KEY", "***REMOVED***")
        self.url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        self.default_model = "doubao-seed-character-251128"
        self._call_count = 0
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=2, min=3, max=6))
    def chat(self, messages, model=None, max_tokens=500, temperature=0.7):
        """调用豆包 Ark API"""
        use_model = model or self.default_model
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": use_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        response = requests.post(self.url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        
        self._call_count += 1
        
        # 提取响应内容
        content = result["choices"][0]["message"]["content"]
        
        # 提取 token 使用量
        usage = result.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        
        return {
            "content": content,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens
        }
    
    def generate_content(self, prompt):
        """便捷方法：生成内容"""
        messages = [{"role": "user", "content": prompt}]
        result = self.chat(messages)
        return result["content"]


# 测试客户端
if __name__ == "__main__":
    client = DoubaoArkClient()
    result = client.chat([
        {"role": "system", "content": "你是一个幽默的旅行博主，来自成都。"},
        {"role": "user", "content": "用幽默的方式介绍一下成都"}
    ])
    print("响应内容:", result["content"])
    print("Token使用:", result["input_tokens"], "输入 +", result["output_tokens"], "输出")