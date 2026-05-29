import sys
import io
import os
import logging
from datetime import datetime
import csv
from typing import Dict, List
from ai_editor import AIEditor

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def update_csv_status(processed_ids: List[str]):
    csv_path = "content/social_media_dataset_cbt_2026.csv"
    if os.path.exists(csv_path):
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        for row in rows:
            if row.get('Task_ID') in processed_ids:
                row['Status'] = 'Published'
        
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys() if rows else [])
            writer.writeheader()
            writer.writerows(rows)
        
        logger.info(f"CSV 已更新，标记 {len(processed_ids)} 条为已发布")

def main():
    print("\n" + "="*80)
    print("                    ChinaBound Travel 每周更新")
    print("="*80)
    
    editor = AIEditor()
    saved_files = editor.full_ai_editing_pipeline()
    
    if saved_files:
        processed_ids = []
        for content in editor.select_weekly_content(5):
            processed_ids.append(content.get('id', ''))
        
        update_csv_status(processed_ids)
    
    print("\n" + "="*80)
    print("每周更新完成！")
    print(f"生成了 {len(saved_files)} 篇新文章")
    print("="*80)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
