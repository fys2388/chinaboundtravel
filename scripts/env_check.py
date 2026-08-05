#!/usr/bin/env python3
"""
环境变量验证脚本 - 检查所有必要的API密钥和配置
"""

import os
import sys
import json
from pathlib import Path

# 必需的环境变量（按重要性排序）
REQUIRED_VARS = [
    # 基础设施（必须）
    ("CLOUDFLARE_API_TOKEN", "Cloudflare部署"),
    ("CLOUDFLARE_ZONE_ID", "Cloudflare CDN"),
    ("FEISHU_WEBHOOK_URL", "飞书通知"),
    
    # AI服务（必须）
    ("DOUBAO_ARK_API_KEY", "豆包AI生成"),
    ("DEEPSEEK_API_KEY", "DeepSeek辅助"),
    
    # 数据分析（必须）
    ("GA4_API_KEY", "Google Analytics"),
    ("GA4_PROPERTY_ID", "GA4属性ID"),
    ("GSC_SERVICE_ACCOUNT_JSON", "Google Search Console"),
    
    # 营销（必须）
    ("TRAVELPAYOUTS_API_TOKEN", "联盟营销"),
    ("TRAVELPAYOUTS_MARKER", "联盟标记"),
    ("MAILERLITE_API_TOKEN", "邮件营销"),
    
    # 支付（必须）
    ("STRIPE_SECRET_KEY", "Stripe支付"),
    ("STRIPE_WEBHOOK_SECRET", "Stripe回调"),
    ("RESEND_API_KEY", "邮件发送"),
]

# 可选的环境变量
OPTIONAL_VARS = [
    ("BUFFER_API_TOKEN", "Buffer社媒管理"),
    ("FACEBOOK_PAGE_ID", "Facebook发布"),
    ("FACEBOOK_PAGE_ACCESS_TOKEN", "Facebook发布"),
    ("TWITTER_BEARER_TOKEN", "Twitter发布"),
    ("LINKEDIN_ACCESS_TOKEN", "LinkedIn发布"),
    ("YOUTUBE_OAUTH_REFRESH_TOKEN", "YouTube上传"),
    ("NORDVPN_API_KEY", "VPN联盟"),
    ("NORDVPN_AFFILIATE_ID", "VPN联盟"),
]


def load_env():
    """加载.env文件"""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip().strip('"').strip("'")


def check_var(name: str, description: str) -> dict:
    """检查单个环境变量"""
    value = os.getenv(name, "")
    
    # 检查是否为空
    if not value:
        return {
            "name": name,
            "description": description,
            "status": "MISSING",
            "present": False,
            "length": 0
        }
    
    # 检查是否为默认值
    if value.startswith("your-") or value.startswith("REPLACE_WITH_YOUR"):
        return {
            "name": name,
            "description": description,
            "status": "DEFAULT",
            "present": True,
            "length": len(value)
        }
    
    # 检查密钥格式（简单验证）
    status = "VALID"
    if name.endswith("_KEY") and len(value) < 10:
        status = "SHORT"
    
    return {
        "name": name,
        "description": description,
        "status": status,
        "present": True,
        "length": len(value)
    }


def main():
    print("=" * 60)
    print("🔍 环境变量验证报告")
    print("=" * 60)
    print(f"时间: {Path(__file__).parent.parent.name}")
    
    load_env()
    
    print("\n📋 必需的环境变量:")
    print("-" * 60)
    
    missing = []
    default = []
    valid = []
    
    for var, desc in REQUIRED_VARS:
        result = check_var(var, desc)
        status_icon = "✅" if result["status"] == "VALID" else "❌"
        print(f"{status_icon} {var:30} - {result['status']:8} ({desc})")
        
        if result["status"] == "MISSING":
            missing.append(var)
        elif result["status"] == "DEFAULT":
            default.append(var)
        else:
            valid.append(var)
    
    print("\n📦 可选的环境变量:")
    print("-" * 60)
    
    optional_present = []
    optional_missing = []
    
    for var, desc in OPTIONAL_VARS:
        result = check_var(var, desc)
        status_icon = "⚠️" if result["present"] else "  "
        print(f"{status_icon} {var:30} - {result['status']:8} ({desc})")
        
        if result["present"]:
            optional_present.append(var)
        else:
            optional_missing.append(var)
    
    # 生成报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "required": {
            "valid": len(valid),
            "missing": len(missing),
            "default": len(default),
            "total": len(REQUIRED_VARS)
        },
        "optional": {
            "present": len(optional_present),
            "missing": len(optional_missing),
            "total": len(OPTIONAL_VARS)
        }
    }
    
    print("\n" + "=" * 60)
    print("📊 验证结果汇总")
    print("=" * 60)
    print(f"必需变量: {len(valid)}/{len(REQUIRED_VARS)} 有效")
    if missing:
        print(f"  ❌ 缺失: {', '.join(missing)}")
    if default:
        print(f"  ⚠️  默认值: {', '.join(default)}")
    print(f"\n可选变量: {len(optional_present)}/{len(OPTIONAL_VARS)} 已配置")
    
    # 保存报告
    report_dir = Path(__file__).parent.parent / "reports" / "env-check"
    report_dir.mkdir(parents=True, exist_ok=True)
    
    report_file = report_dir / f"env-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 报告已保存: {report_file}")
    
    # 返回退出码
    if missing or default:
        print("\n❌ 验证失败：存在缺失或默认的必需环境变量")
        return 1
    else:
        print("\n✅ 验证通过：所有必需环境变量已正确配置")
        return 0


if __name__ == "__main__":
    from datetime import datetime
    sys.exit(main())
