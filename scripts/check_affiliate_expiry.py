import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_klook_expiry():
    hugo_toml_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'hugo.toml')
    
    if not os.path.exists(hugo_toml_path):
        print("❌ hugo.toml not found")
        return False
    
    with open(hugo_toml_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    import re
    match = re.search(r"klook_expire_date\s*=\s*[\"']([^\"']+)[\"']", content)
    if not match:
        print("❌ klook_expire_date not found in hugo.toml")
        return False
    
    expire_date_str = match.group(1)
    try:
        expire_date = datetime.strptime(expire_date_str, '%Y-%m-%d').date()
    except ValueError:
        print(f"❌ Invalid date format: {expire_date_str}")
        return False
    
    today = datetime.now().date()
    days_left = (expire_date - today).days
    
    print(f"[KLOOK CHECK] Expiry date: {expire_date}")
    print(f"[KLOOK CHECK] Days remaining: {days_left}")
    
    if days_left <= 0:
        print("[KLOOK CHECK] WARNING: Klook link has expired! Please update immediately!")
        return True
    elif days_left <= 7:
        print(f"[KLOOK CHECK] WARNING: Klook link expires in {days_left} days! Please update soon!")
        return True
    else:
        print(f"[KLOOK CHECK] OK: Klook link is valid for {days_left} more days")
        return False

if __name__ == "__main__":
    expired = check_klook_expiry()
    sys.exit(1 if expired else 0)