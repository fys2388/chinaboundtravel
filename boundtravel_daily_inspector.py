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
import sys
import argparse
from datetime import date, timedelta

sys.stdout.reconfigure(encoding='utf-8')

class BoundTravelInspector:
    def __init__(self):
        self.base_url = "https://www.chinaboundtravel.com"
        self.results = {}
        self.webhook_url = os.environ.get('FEISHU_WEBHOOK_URL', '')
        self.check_affiliate = False
        self.weekly_report = False
    
    def check_website_accessibility(self):
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
        result = {"status": "OK", "broken_links": [], "total_checked": 0}
        
        import re
        import glob
        
        for filepath in glob.glob("content/**/*.md", recursive=True):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                links = re.findall(r'\[.*?\]\(([^)]+)\)', content)
                for link in links:
                    if link.startswith('/') and not link.startswith('//'):
                        result["total_checked"] += 1
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
    
    def check_affiliate_links(self):
        result = {"status": "OK", "broken_links": [], "total_checked": 0, "affiliate_domains": []}
        
        affiliate_patterns = [
            'shareasale.com',
            'cj.com',
            'rakuten.com',
            'awin.com',
            'impactradius.com',
            'skyscanner.com',
            'booking.com',
            'agoda.com',
            'tripadvisor.com',
            'viator.com',
            'getyourguide.com',
            'klook.com'
        ]
        
        import re
        import glob
        
        for filepath in glob.glob("content/**/*.md", recursive=True):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                links = re.findall(r'\[.*?\]\(([^)]+)\)', content)
                for link in links:
                    if any(pattern in link for pattern in affiliate_patterns):
                        result["total_checked"] += 1
                        result["affiliate_domains"].append(link)
                        try:
                            response = requests.head(link, timeout=15, allow_redirects=True)
                            if response.status_code not in [200, 301, 302, 307, 308]:
                                result["broken_links"].append(f"{filepath}: {link} (HTTP {response.status_code})")
                        except Exception as e:
                            result["broken_links"].append(f"{filepath}: {link} ({str(e)})")
            except Exception:
                pass
        
        if result["broken_links"]:
            result["status"] = "ERROR"
        
        self.results["affiliate_links"] = result
        return result
    
    def generate_report(self, report_type="daily"):
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
            
            if "details" in value:
                if isinstance(value["details"], list):
                    report += "- 详情:\n"
                    for detail in value["details"]:
                        report += f"  - {detail}\n"
                else:
                    report += f"- 详情: {value['details']}\n"
            
            if "files_with_issues" in value:
                report += f"- 问题文件数: {len(value['files_with_issues'])}\n"
                report += f"- 总问题数: {value.get('total_issues', 0)}\n"
            
            if "broken_links" in value:
                report += f"- 检查链接数: {value.get('total_checked', 0)}\n"
                report += f"- 无效链接数: {len(value['broken_links'])}\n"
            
            report += "\n"
        
        report += "## 总结\n\n"
        if all_ok:
            report += "✅ **所有检查通过！网站运行正常。**\n"
        else:
            report += "⚠️ **部分检查未通过，请查看详情。**\n"
        
        report += f"\n---\n*报告生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        
        return report
    
    def send_to_feishu(self, message):
        if not self.webhook_url:
            print("Feishu webhook not configured, skipping...")
            return False
        
        try:
            payload = {
                "msg_type": "markdown",
                "content": {
                    "text": message[:4096]
                }
            }
            response = requests.post(self.webhook_url, json=payload, timeout=30)
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to send to Feishu: {e}")
            return False
    
    def save_report(self, report, report_type):
        today = date.today()
        os.makedirs("reports", exist_ok=True)
        filename = f"reports/{today.strftime('%Y%m%d')}_{report_type}.md"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        return filename

def main():
    parser = argparse.ArgumentParser(description='ChinaBound Travel Daily Inspector')
    parser.add_argument('--check-affiliate', action='store_true', help='Check affiliate links')
    parser.add_argument('--weekly-report', action='store_true', help='Force weekly report mode')
    args = parser.parse_args()
    
    inspector = BoundTravelInspector()
    inspector.check_affiliate = args.check_affiliate
    inspector.weekly_report = args.weekly_report
    
    print("Running daily inspection...")
    
    inspector.check_website_accessibility()
    inspector.check_ssl_certificate()
    inspector.check_sitemap()
    inspector.check_redirects()
    inspector.check_garbled_chars()
    inspector.check_internal_links()
    
    if args.check_affiliate:
        print("Checking affiliate links...")
        inspector.check_affiliate_links()
    
    today = date.today()
    report_type = "daily"
    
    if args.weekly_report or today.weekday() == 6:
        report_type = "weekly"
    
    if today.day == 1:
        report_type = "monthly"
    
    report = inspector.generate_report(report_type)
    print(report)
    
    filename = inspector.save_report(report, report_type)
    print(f"Report saved to: {filename}")
    
    if inspector.send_to_feishu(report):
        print("Report sent to Feishu successfully!")
    else:
        print("Feishu notification skipped or failed")

if __name__ == "__main__":
    main()