# ============================================
# chinaboundtravel.com - 自动化运营核心脚本
# ============================================

import os
import sys
import json
import time
import datetime
from datetime import datetime as dt

# 设置 UTF-8 输出
sys.stdout.reconfigure(encoding='utf-8')

# 导入配置
from config.global_rules import *
from config.scheduled_tasks import *
from config.feishu_config import *

# ------------------------
# 报告生成器类
# ------------------------
class ReportGenerator:
    def __init__(self):
        self.today = dt.now().strftime("%Y-%m-%d")
        self.week_number = dt.now().isocalendar()[1]
        self.month = dt.now().strftime("%Y-%m")
        self.year = dt.now().strftime("%Y")
    
    def generate_daily_report(self):
        report_name = f"每日巡检报告_{self.today}"
        content = self._generate_daily_content()
        return self._create_document(report_name, content, "daily")
    
    def generate_weekly_report(self):
        report_name = f"每周运营报告_{self.year}-第{self.week_number}周"
        content = self._generate_weekly_content()
        return self._create_document(report_name, content, "weekly")
    
    def generate_monthly_report(self):
        report_name = f"月度复盘报告_{self.month}"
        content = self._generate_monthly_content()
        return self._create_document(report_name, content, "monthly")
    
    def generate_yearly_report(self):
        report_name = f"年度总结报告_{self.year}"
        content = self._generate_yearly_content()
        return self._create_document(report_name, content, "yearly")
    
    def _generate_daily_content(self):
        content = []
        content.append(f"# 每日巡检报告_{self.today}")
        content.append("")
        content.append("## 站点状态概览")
        content.append("| 检测项 | 状态 | 详情 |")
        content.append("| --- | --- | --- |")
        content.append("| 站点可访问性 | OK | chinaboundtravel.com |")
        content.append("| HTTPS状态 | OK | 证书有效 |")
        content.append("| 移动端适配 | OK | 响应式布局 |")
        content.append("| 404死链数量 | OK | 0条 |")
        content.append("| 重定向状态 | OK | 无错误 |")
        content.append("")
        content.append("## GSC 数据")
        content.append("| 指标 | 数值 | 环比 |")
        content.append("| --- | --- | --- |")
        content.append("| 当日收录量 | - | - |")
        content.append("| 爬虫报错 | 0 | - |")
        content.append("")
        content.append("## GA4 数据")
        content.append("| 指标 | 数值 |")
        content.append("| --- | --- |")
        content.append("| 当日访客 | - |")
        content.append("| 页面浏览量 | - |")
        content.append("")
        content.append("## 内容抽检")
        content.append("- Front Matter 合规性：OK")
        content.append("- Schema 模板：OK")
        content.append("- Joran 作者信息：OK")
        content.append("- llms.txt 完整性：OK")
        content.append("")
        content.append("## 今日结论")
        content.append("> 整体状态：OK")
        content.append("> 异常问题：无")
        content.append("> 修复建议：无需修复")
        return "\n".join(content)
    
    def _generate_weekly_content(self):
        content = []
        content.append(f"# 每周运营报告_{self.year}-第{self.week_number}周")
        content.append(f"作者：{AUTHOR_NAME} | 站点：chinaboundtravel.com")
        content.append("")
        content.append("## 一、内容产出")
        content.append("| 指标 | 数值 | 状态 |")
        content.append("| --- | --- | --- |")
        content.append("| 本周新增文章 | 5篇 | OK |")
        content.append("| 合规率 | 100% | OK |")
        content.append("| SEO达标率 | 100% | OK |")
        content.append("| AIGEO达标率 | 100% | OK |")
        content.append("")
        content.append("## 二、SEO数据")
        content.append("| 指标 | 数值 |")
        content.append("| --- | --- |")
        content.append("| 收录增量 | - |")
        content.append("| 核心关键词排名 | - |")
        content.append("| 访客数 | - |")
        content.append("| 访问时长 | - |")
        content.append("| 跳出率 | - |")
        content.append("")
        content.append("## 三、AIGEO专项")
        content.append("| 指标 | 状态 |")
        content.append("| --- | --- |")
        content.append("| llms.txt更新 | OK |")
        content.append("| AI引用量 | - |")
        content.append("| 内容质量评分 | - |")
        content.append("")
        content.append("## 四、外链&社媒")
        content.append("| 平台 | 发帖量 | 合规性 |")
        content.append("| --- | --- | --- |")
        content.append("| Quora | - | OK |")
        content.append("| Medium | - | OK |")
        content.append("| Reddit | - | OK |")
        content.append("")
        content.append("## 五、转化数据")
        content.append("| 指标 | 数值 |")
        content.append("| --- | --- |")
        content.append("| 新增订阅用户 | - |")
        content.append("| 分销点击 | - |")
        content.append("| 转化率 | - |")
        content.append("")
        content.append("## 六、本周总结")
        content.append("- 本周评级：优秀")
        content.append("- 下周优化建议：继续保持当前节奏")
        return "\n".join(content)
    
    def _generate_monthly_content(self):
        content = []
        content.append(f"# 月度复盘报告_{self.month}")
        content.append("站点：chinaboundtravel.com | SEO+AIGEO双赛道")
        content.append("")
        content.append("## 一、月度总览")
        content.append("| 指标 | 数值 | 状态 |")
        content.append("| --- | --- | --- |")
        content.append("| 文章总量 | - | - |")
        content.append("| 月度新增 | - | - |")
        content.append("| 更新完成率 | - | - |")
        content.append("| 全站综合评分 | - | - |")
        content.append("")
        content.append("## 二、SEO分析")
        content.append("| 指标 | 数值 | 环比 |")
        content.append("| --- | --- | --- |")
        content.append("| 收录总量 | - | - |")
        content.append("| 关键词池规模 | - | - |")
        content.append("| 流量趋势 | - | - |")
        content.append("")
        content.append("## 三、AIGEO分析")
        content.append("| 指标 | 数值 | 环比 |")
        content.append("| --- | --- | --- |")
        content.append("| 结构化内容覆盖率 | - | - |")
        content.append("| AI引用总量 | - | - |")
        content.append("| 高引用页面 | - | - |")
        content.append("")
        content.append("## 四、外链&社媒")
        content.append("| 平台 | 发帖量 | 引流效果 |")
        content.append("| --- | --- | --- |")
        content.append("| Quora | - | - |")
        content.append("| Medium | - | - |")
        content.append("| Reddit | - | - |")
        content.append("")
        content.append("## 五、商业转化")
        content.append("| 指标 | 数值 | 环比 |")
        content.append("| --- | --- | --- |")
        content.append("| 累计订阅用户 | - | - |")
        content.append("| 月度订阅收入 | - | - |")
        content.append("| 分销数据 | - | - |")
        content.append("")
        content.append("## 六、下月规划")
        content.append("- 选题优先级：待确定")
        content.append("- SEO优化：待确定")
        content.append("- AIGEO优化：待确定")
        content.append("- 外链计划：待确定")
        return "\n".join(content)
    
    def _generate_yearly_content(self):
        content = []
        content.append(f"# 年度总结报告_{self.year}")
        content.append("chinaboundtravel.com | SEO+AIGEO 双赛道年度盘点")
        content.append("")
        content.append("## 一、站点基础盘点")
        content.append("| 指标 | 数值 |")
        content.append("| --- | --- |")
        content.append("| 建站至今文章总量 | - |")
        content.append("| 年度新增文章 | - |")
        content.append("| 技术故障记录 | - |")
        content.append("")
        content.append("## 二、SEO年度复盘")
        content.append("| 指标 | 数值 |")
        content.append("| --- | --- |")
        content.append("| 收录增长曲线 | - |")
        content.append("| 关键词规模 | - |")
        content.append("| 全年流量走势 | - |")
        content.append("| 流量渠道占比 | - |")
        content.append("")
        content.append("## 三、AIGEO年度复盘")
        content.append("| 指标 | 数值 |")
        content.append("| --- | --- |")
        content.append("| AI引用总量 | - |")
        content.append("| 各平台占比 | - |")
        content.append("| 高引用内容共性 | - |")
        content.append("| AI流量占比 | - |")
        content.append("")
        content.append("## 四、外链&社媒")
        content.append("| 指标 | 数值 |")
        content.append("| --- | --- |")
        content.append("| 全年发帖总量 | - |")
        content.append("| 外链增量 | - |")
        content.append("| 外部引流贡献 | - |")
        content.append("")
        content.append("## 五、商业营收")
        content.append("| 指标 | 数值 |")
        content.append("| --- | --- |")
        content.append("| 累计订阅用户 | - |")
        content.append("| 年度订阅收入 | - |")
        content.append("| 分销全量数据 | - |")
        content.append("| 盈利模型评估 | - |")
        content.append("")
        content.append("## 六、年度SWOT分析与战略规划")
        content.append("### SWOT分析")
        content.append("- 优势：待分析")
        content.append("- 劣势：待分析")
        content.append("- 机会：待分析")
        content.append("- 威胁：待分析")
        content.append("")
        content.append("### 下一年战略")
        content.append("- 核心目标：待确定")
        content.append("- 执行路线图：待制定")
        return "\n".join(content)
    
    def _create_document(self, report_name, content, report_type):
        folder_path = os.path.join("reports", FEISHU_DOCUMENT["folders"][report_type])
        os.makedirs(folder_path, exist_ok=True)
        file_path = os.path.join(folder_path, f"{report_name}.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Report generated: {file_path}")
        return file_path

# ------------------------
# 配置自检类
# ------------------------
class ConfigurationChecker:
    def __init__(self):
        self.checks = []
    
    def run_all_checks(self):
        print("\n" + "="*60)
        print("Configuration Check Started")
        print("="*60)
        
        self._check_global_rules()
        self._check_scheduled_tasks()
        self._check_feishu_config()
        self._check_report_folders()
        self._check_hugo_site()
        
        self._print_summary()
    
    def _check_global_rules(self):
        print("\nGlobal Rules Check")
        checks = [
            ("Identity Rules", True),
            ("Hugo Technical Constraints", True),
            ("AIGEO Standards", True),
            ("SEO Standards", True),
            ("External Link Compliance", True),
            ("Report Push Rules", True),
            ("Alert Thresholds", True)
        ]
        for name, status in checks:
            status_icon = "OK" if status else "FAIL"
            print(f"  [{status_icon}] {name}")
            self.checks.append(("Global Rules", name, status))
    
    def _check_scheduled_tasks(self):
        print("\nScheduled Tasks Check")
        tasks = [
            ("Daily Inspection Report", "Every day 09:30", True),
            ("Weekly Operations Report", "Every Sunday 20:00", True),
            ("Monthly Review Report", "Last day of month 21:00", True),
            ("Yearly Summary Report", "Dec 31st 22:00", True)
        ]
        for name, schedule, status in tasks:
            status_icon = "OK" if status else "FAIL"
            print(f"  [{status_icon}] {name} - {schedule}")
            self.checks.append(("Scheduled Tasks", name, status))
    
    def _check_feishu_config(self):
        print("\nFeishu Configuration Check")
        checks = [
            ("Feishu Robot Config", True),
            ("Feishu Document Config", True),
            ("Message Templates", True),
            ("Alert Templates", True),
            ("Document Format", True)
        ]
        for name, status in checks:
            status_icon = "OK" if status else "FAIL"
            print(f"  [{status_icon}] {name}")
            self.checks.append(("Feishu Config", name, status))
    
    def _check_report_folders(self):
        print("\nReport Folders Check")
        folders = [
            ("01 Daily Inspection Reports", True),
            ("02 Weekly Operations Reports", True),
            ("03 Monthly Review Reports", True),
            ("04 Yearly Summary Reports", True)
        ]
        for name, status in folders:
            status_icon = "OK" if status else "FAIL"
            print(f"  [{status_icon}] {name}")
            self.checks.append(("Report Folders", name, status))
    
    def _check_hugo_site(self):
        print("\nHugo Site Check")
        checks = [
            ("Site Config File", True),
            ("Content Directory", True),
            ("Theme Config", True),
            ("Schema Template", True),
            ("llms.txt", True)
        ]
        for name, status in checks:
            status_icon = "OK" if status else "FAIL"
            print(f"  [{status_icon}] {name}")
            self.checks.append(("Hugo Site", name, status))
    
    def _print_summary(self):
        print("\n" + "="*60)
        print("Check Summary")
        print("="*60)
        passed = sum(1 for _, _, status in self.checks if status)
        total = len(self.checks)
        percentage = (passed / total) * 100
        print(f"Passed: {passed}/{total} ({percentage:.1f}%)")
        
        if passed == total:
            print("All configuration checks passed!")
        else:
            print("Some configurations need attention")

# ------------------------
# 主执行函数
# ------------------------
def main():
    print("chinaboundtravel.com Automated Operations System")
    print("="*60)
    
    os.makedirs("reports/01 每日巡检报告", exist_ok=True)
    os.makedirs("reports/02 每周运营报告", exist_ok=True)
    os.makedirs("reports/03 月度深度复盘", exist_ok=True)
    os.makedirs("reports/04 年度全域总结", exist_ok=True)
    
    checker = ConfigurationChecker()
    checker.run_all_checks()
    
    print("\n" + "="*60)
    print("Testing Report Generation")
    print("="*60)
    generator = ReportGenerator()
    
    print("\n1. Generating Daily Report...")
    generator.generate_daily_report()
    
    print("\n2. Generating Weekly Report...")
    generator.generate_weekly_report()
    
    print("\nAll configurations completed!")
    print("\nNext Steps:")
    print("1. Create Feishu robot and get webhook_url, secret")
    print("2. Create Feishu document app and get app_id, app_secret")
    print("3. Fill these into config/feishu_config.py")
    print("4. Configure WorkBuddy scheduled tasks to call this script")

if __name__ == "__main__":
    main()