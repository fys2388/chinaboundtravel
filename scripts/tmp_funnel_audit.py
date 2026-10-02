# 临时脚本：转化漏斗审计（用完即删）
import json, re

d = json.load(open("reports/real_data/ga4_real_data.json", encoding="utf-8"))
print("GA4 抓取时间:", d.get("pull_time") or d.get("data_date"))
print()
print("=== 指标 ===")
for k, v in (d.get("metrics") or {}).items():
    print(f"  {k} = {v}")
print()
s = json.dumps(d, ensure_ascii=False)
names = sorted(set(re.findall(r'"(affiliate[^"]*|lead_magnet[^"]*|subscribe[^"]*)"', s)))
print("=== 相关事件名 ===")
for n in names:
    print(" ", n)
print()
# 找 events 数组
ev = d.get("events") or d.get("custom_events") or []
if ev:
    print("=== 事件明细 ===")
    for e in ev[:40]:
        print(" ", json.dumps(e, ensure_ascii=False)[:160])
