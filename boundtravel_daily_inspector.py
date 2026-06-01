#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChinaBound Travel Daily Inspector
Supports daily/weekly/monthly reports with Feishu notification
"""

import requests
import os
import json
import datetime
from datetime import date, timedelta

class BoundTravelInspector:
    def __init__(self):
        self.base_url = "https://www.chinaboundtravel.com"
        self.results = {}
        self.webhook_url = os.environ.get('FEISHU_WEBHOOK_URL', '')
    
    def check_website_accessibility(self):
        """检查网站可访问性"""
        result = {"status": "OK", "details": ""}
        try:
            response = requests.get(self.base_url, timeout=30)
            if response.status_code == 200:
                result["details"] = f"Status: {response.status_code}, Response time: {response.elapsed.total_seconds():.2f}s"
            else:
                result["status"] = "ERROR"
                result["details"] = f"HTTP {response.status_code}"
        except Exception as e:
            result["status"] = "ERROR"
            result["details"] = str(e)
        self.results["accessibility"] = result
        return result
    
    def check_ssl_certificate(self):
        """检查SSL证书"""
        result = {"status": "OK", "details": ""}
        try:
            import ssl
            import socket
            context = ssl.create_default_context()
            with socket.create_connection(("www.chinaboundtravel.com", 443)) as sock:
                with context.wrap_socket(sock, server_hostname="www.chinaboundtravel.com") as secure_sock:
                    cert = secure_sock.getpeercert()
                    expire_date = datetime.datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y GMT')
                    days_left = (expire_date - datetime.datetime.now()).days
                    if days_left > 30:
                        result["details"] = f"Valid until: {expire_date.strftime('%Y-%m-%d')} ({days_left} days left)"
                    else:
                        result["status"] = "WARNING"
                        result["details"] = f"Expires soon: {expire_date.strftime('%Y-%m-%d')} ({days_left} days left)"
        except Exception as e:
            result["status"] = "ERROR"
            result["details"] = str(e)
        self.results["ssl"] = result
        return result
    
    def check_sitemap(self):
        """检查sitemap"""
        result = {"status": "OK", "details": ""}
        try:
            response = requests.get(f"{self.base_url}/sitemap.xml", timeout=30)
            if response.status_code == 200:
                import re
                url_count = len(re.findall(r'<loc>', response.text))
                result["details"] = f"{url_count} URLs found"
            else:
                result["status"] = "ERROR"
                result["details"] = f"HTTP {response.status_code}"
        except Exception as e:
            result["status"] = "ERROR"
            result["details"] = str(e)
        self.results["sitemap"] = result
        return result
    
    def check_redirects(self):
        """检查重定向"""
        result = {"status": "OK", "details": []}
        urls = [
            ("http://chinaboundtravel.com", "https://www.chinaboundtravel.com"),
            ("http://www.chinaboundtravel.com", "https://www.chinaboundtravel.com"),
            ("https://chinaboundtravel.com", "https://www.chinaboundtravel.com")
        ]
        
        for source, expected in urls:
            try:
                response = requests.get(source, allow_redirects=True, timeout=30)
                final_url = response.url
                if final_url.startswith(expected):
                    result["details"].append(f"✅ {source} -> {final_url}")
                else:
                    result["details"].append(f"⚠️ {source} -> {final_url} (expected: {expected})")
                    result["status"] = "WARNING"
            except Exception as e:
                result["details"].append(f"❌ {source}: {str(e)}")
                result["status"] = "ERROR"
        
        self.results["redirects"] = result
        return result
    
    def check_garbled_chars(self):
        """检查乱码字符"""
        result = {"status": "OK", "files_with_issues": [], "total_issues": 0}
        garble_chars = ['\uFFFD', '\u00A0', '\u200B', '\u2028', '\u2029']
        
        import glob
        for filepath in glob.glob("content/**/*.md", recursive=True):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                for char in garble_chars:
                    count = content.count(char)
                    if count > 0:
                        result["files_with_issues"].append(f"{filepath}: {count} garbled chars")
                        result["total_issues"] += count
            except Exception:
                pass
        
        if result["files_with_issues"]:
            result["status"] = "ERROR"
        
        self.results["garbled_chars"] = result
        return result
    
    def check_internal_links(self):
        """检查内链"""
        result = {"status": "OK", "broken_links": [], "total_checked": 0}
        
        import re
        import glob
        
        for filepath in glob.glob("content/**/*.md", recursive=True):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 查找 markdown 链接
                links = re.findall(r'\[.*?\]\(([^)]+)\)', content)
                for link in links:
                    if link.startswith('/') and not link.startswith('//'):
                        result["total_checked"] += 1
                        # 检查链接是否有效
                        if '#' in link:
                            link = link.split('#')[0]
                        if not link.endswith('.md') and not link.endswith('/'):
                            link += '/'
                        try:
                            url = self.base_url + link
                            response = requests.head(url, timeout=10)
                            if response.status_code not in [200, 301, 302]:
                                result["broken_links"].append(f"{filepath}: {link} (HTTP {response.status_code})")
                        except Exception as e:
                            result["broken_links"].append(f"{filepath}: {link} ({str(e)})")
            except Exception:
                pass
        
        if result["broken_links"]:
            result["status"] = "ERROR"
        
        self.results["internal_links"] = result
        return result
    
    def generate_report(self, report_type="daily"):
        """生成报告"""
        today = date.today()
        report_title = {
            "daily": f"📅 每日巡检报告 - {today.strftime('%Y年%m月%d日')}",
            "weekly": f"📊 周报 - {today.strftime('%Y年第%W周')}",
            "monthly": f"📈 月报 - {today.strftime('%Y年%m月')}"
        }
        
        report = f"# {report_title[report_type]}\n\n"
        report += "## 网站状态\n\n"
        
        all_ok = True
        for key, value in self.results.items():
            status_icon = "✅" if value["status"] == "OK" else "⚠️" if value["status"] == "WARNING" else "❌"
            if value["status"] != "OK":
                all_ok = False
            
            report += f"### {key.replace('_', ' ').title()}\n"
            report += f"- 状态: {status_icon} {value['status']}\n"
            
            if isinstance(value["details"], list):
                report += "- 详情:\n"
                for detail in value["details"]:
                    report += f"  - {detail}\n"
            else:
                report += f"- 详情: {value['details']}\n"
            report += "\n"
        
        report += "## 总结\n\n"
        if all_ok:
            report += "✅ **所有检查通过！网站运行正常。**\n"
        else:
            report += "⚠️ **部分检查未通过，请查看详情。**\n"
        
        report += f"\n---\n*报告生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        
        return report
    
    def send_to_feishu(self, message):
        """发送消息到飞书"""
        if not self.webhook_url:
            print("Feishu webhook not configured, skipping...")
            return False
        
        try:
            payload = {
                "msg_type": "markdown",
                "content": {
                    "text": message[:4096]  # 飞书限制
                }
            }
            response = requests.post(self.webhook_url, json=payload, timeout=30)
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to send to Feishu: {e}")
            return False
    
    def save_report(self, report, report_type):
        """保存报告到文件"""
        today = date.today()
        filename = f"reports/{today.strftime('%Y%m%d')}_{report_type}.md"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        return filename

def main():
    inspector = BoundTravelInspector()
    
    print("Running daily inspection...")
    
    # 执行所有检查
    inspector.check_website_accessibility()
    inspector.check_ssl_certificate()
    inspector.check_sitemap()
    inspector.check_redirects()
    inspector.check_garbled_chars()
    inspector.check_internal_links()
    
    # 判断报告类型
    today = date.today()
    report_type = "daily"
    
    # 判断周报（周日）
    if today.weekday() == 6:  # Sunday
        report_type = "weekly"
    
    # 判断月报（每月1号）
    if today.day == 1:
        report_type = "monthly"
    
    # 生成报告
    report = inspector.generate_report(report_type)
    print(report)
    
    # 保存报告
    filename = inspector.save_report(report, report_type)
    print(f"Report saved to: {filename}")
    
    # 发送到飞书
    if inspector.send_to_feishu(report):
        print("Report sent to Feishu successfully!")
    else:
        print("Feishu notification skipped or failed")

if __name__ == "__main__":
    main()