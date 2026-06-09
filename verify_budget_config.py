#!/usr/bin/env python3
"""
验证预算配置和模型限制脚本
检查所有 DeepSeek API 调用是否都使用 deepseek-chat 模型
"""

import os
import sys
import re
import io
from pathlib import Path

# 设置标准输出编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def find_deepseek_calls(root_path):
    """查找所有可能调用 DeepSeek 的代码"""
    calls = []
    
    for filepath in root_path.rglob("*.py"):
        if "deprecated_scripts" in str(filepath):
            continue
            
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # 查找模型配置
                model_matches = re.findall(r'model\s*[=:]\s*["\']([^"\']+)["\']', content)
                for model in model_matches:
                    if 'deepseek' in model.lower() and model != 'deepseek-chat':
                        calls.append({
                            'file': str(filepath),
                            'type': 'model_config',
                            'value': model,
                            'line': content.count('\n', 0, content.find(f'model={model}')) + 1
                        })
                
                # 查找 API URL 调用
                if 'api.deepseek.com' in content:
                    calls.append({
                        'file': str(filepath),
                        'type': 'api_call',
                        'value': 'api.deepseek.com',
                        'line': content.count('\n', 0, content.find('api.deepseek.com')) + 1
                    })
                    
        except Exception as e:
            continue
    
    return calls

def main():
    print("=" * 70)
    print("  DeepSeek 预算配置验证脚本")
    print("=" * 70)
    
    # 检查预算控制器配置
    try:
        from chinaboundtravel_social_bot.budget_controller import MODEL_PRICING, ALLOWED_MODELS, BudgetController
        print("\n✅ 预算控制器模块加载成功")
        print(f"\n📋 允许的模型: {ALLOWED_MODELS}")
        print("\n💰 模型定价表:")
        for model, prices in MODEL_PRICING.items():
            status = "OK" if model in ALLOWED_MODELS else "DISABLED"
            print(f"  [{status}] {model}: 输入¥{prices['input']}/M + 输出¥{prices['output']}/M")
        
        print("\n🔍 预算检查:")
        controller = BudgetController()
        print(f"  允许调用 deepseek-chat: {controller.can_call_api('deepseek-chat')}")
        print(f"  允许调用 deepseek-v4-flash: {controller.can_call_api('deepseek-v4-flash')}")
        print(f"  允许调用 deepseek-v4-pro: {controller.can_call_api('deepseek-v4-pro')}")
        
    except Exception as e:
        print(f"[ERROR] 预算控制器加载失败: {e}")
        sys.exit(1)
    
    # 搜索所有可能的 DeepSeek 调用
    print("\n" + "=" * 70)
    print("  搜索代码中的 DeepSeek 调用...")
    print("=" * 70)
    
    root = Path(__file__).parent
    calls = find_deepseek_calls(root)
    
    if calls:
        print("\n⚠️ 发现以下潜在问题:")
        for call in calls:
            print(f"\n  文件: {call['file']}")
            print(f"  类型: {call['type']}")
            print(f"  值: {call['value']}")
            print(f"  行号: {call['line']}")
    else:
        print("\n✅ 未发现使用禁用模型的代码")
    
    # 检查环境变量
    print("\n" + "=" * 70)
    print("  环境变量检查")
    print("=" * 70)
    api_key = os.getenv("DEEPSEEK_API_KEY")
    backup_key = os.getenv("DEEPSEEK_BACKUP_API_KEY")
    print(f"  DEEPSEEK_API_KEY: {'✅ 已配置' if api_key else '❌ 未配置'}")
    print(f"  DEEPSEEK_BACKUP_API_KEY: {'✅ 已配置' if backup_key else '❌ 未配置'}")
    
    print("\n" + "=" * 70)
    print("  修复建议")
    print("=" * 70)
    print("""
1. 如果发现高价模型调用，请检查以下位置：
   - Cloudflare Worker（buffer-worker/worker.js）
   - 历史脚本（deprecated_scripts/）
   - 手动测试或其他外部调用

2. 确保所有代码都使用 budget_controller.can_call_api() 进行前置检查

3. 检查 DeepSeek 控制台的 API 密钥使用记录，确认调用来源

4. 考虑在 DeepSeek 平台设置模型白名单限制
""")

if __name__ == "__main__":
    main()