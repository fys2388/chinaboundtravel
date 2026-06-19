#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查 GitHub Actions 部署日志
"""

import requests
import json

REPO_OWNER = "fys2388"
REPO_NAME = "chinaboundtravel"

def get_workflow_runs():
    """获取最近的工作流运行记录"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs"
    params = {
        "per_page": 10,
        "branch": "main"
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"获取工作流失败: {e}")
        return None

def get_workflow_log(workflow_id):
    """获取工作流日志"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs/{workflow_id}/logs"
    
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"获取日志失败: {e}")
        return None

def print_workflow_summary(runs):
    """打印工作流摘要"""
    if not runs or 'workflow_runs' not in runs:
        print("未找到工作流记录")
        return
    
    print("=" * 80)
    print(f"GitHub Actions 部署日志检查")
    print("=" * 80)
    
    for run in runs['workflow_runs'][:5]:
        print(f"\n📋 工作流: {run['name']}")
        print(f"   ID: {run['id']}")
        print(f"   状态: {run['status']}")
        print(f"   结论: {run['conclusion']}")
        print(f"   触发: {run['event']}")
        print(f"   分支: {run['head_branch']}")
        print(f"   提交: {run['head_sha'][:7]}")
        print(f"   创建时间: {run['created_at']}")
        print(f"   链接: {run['html_url']}")
        
        if run['status'] == 'completed' and run['conclusion'] != 'success':
            print(f"   ⚠️  部署失败，正在获取日志...")
            log = get_workflow_log(run['id'])
            if log:
                print("-" * 60)
                print("错误日志片段:")
                lines = log.split('\n')
                # 找出包含错误的行
                error_lines = [line for line in lines if 'error' in line.lower() or 'failed' in line.lower() or 'error' in line]
                if error_lines:
                    for line in error_lines[-10:]:
                        print(f"   {line}")
                else:
                    # 如果没有明显错误，显示最后20行
                    for line in lines[-20:]:
                        print(f"   {line}")
                print("-" * 60)

def main():
    runs = get_workflow_runs()
    if runs:
        print_workflow_summary(runs)
        
        # 检查是否有失败的部署
        failed_runs = [r for r in runs['workflow_runs'] if r['status'] == 'completed' and r['conclusion'] != 'success']
        
        if failed_runs:
            print(f"\n❌ 发现 {len(failed_runs)} 个失败的工作流")
            print("建议检查:")
            print("1. GitHub Secrets 是否正确配置 (CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID)")
            print("2. Stripe Webhook 是否正确配置")
            print("3. Hugo 构建是否有错误")
            print("4. 网络连接是否正常")
        else:
            print("\n✅ 最近的工作流全部成功！")

if __name__ == "__main__":
    main()
