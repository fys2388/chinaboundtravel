#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI自动化视频制作工作流
流程：选题 → 脚本生成 → 语音合成 → 图片生成 → 视频组装 → 多平台分发
"""
import argparse
import uuid
import json
import os
from datetime import datetime
from typing import Dict, List

from config import Config
from script_generator import generate_script, get_pending_topics, load_topic_pool
from voiceover import generate_voiceover
from video_assembler import assemble_video, cleanup_temp_files
from uploader import upload_to_platforms

def update_topic_status(topic_id: str, status: str = "used"):
    try:
        with open(Config.TOPIC_POOL_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        for topic in data.get("topics", []):
            if topic.get("id") == topic_id:
                topic["status"] = status
                topic["used_at"] = datetime.now().isoformat()
                break
        
        with open(Config.TOPIC_POOL_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"Error updating topic status: {e}")
        return False

def process_topic(topic: Dict, platforms: list = None) -> Dict:
    video_id = str(uuid.uuid4())[:8]
    title = topic.get("title", "")
    
    print(f"\n{'='*60}")
    print(f"Processing topic: {title}")
    print(f"Video ID: {video_id}")
    print(f"{'='*60}")
    
    results = {
        "video_id": video_id,
        "topic_title": title,
        "topic_id": topic.get("id", ""),
        "steps": {},
        "success": False
    }
    
    print("\n[Step 1/5] Generating script...")
    try:
        script = generate_script(topic)
        script_path = os.path.join(Config.OUTPUT_DIR, f"{video_id}_script.json")
        with open(script_path, "w", encoding="utf-8") as f:
            json.dump(script, f, ensure_ascii=False, indent=2)
        results["steps"]["script"] = {"status": "success", "path": script_path}
        print(f"✓ Script generated: {script.get('hook', '')[:50]}...")
    except Exception as e:
        results["steps"]["script"] = {"status": "failed", "error": str(e)}
        print(f"✗ Script generation failed: {e}")
        return results
    
    print("\n[Step 2/5] Generating voiceover...")
    try:
        narration = script.get("narration", "")
        voiceover_path = generate_voiceover(narration, video_id)
        if voiceover_path:
            results["steps"]["voiceover"] = {"status": "success", "path": voiceover_path}
            print(f"✓ Voiceover generated: {len(narration)} chars")
        else:
            results["steps"]["voiceover"] = {"status": "failed", "error": "Empty output"}
            print("✗ Voiceover generation failed")
    except Exception as e:
        results["steps"]["voiceover"] = {"status": "failed", "error": str(e)}
        print(f"✗ Voiceover generation failed: {e}")
    
    print("\n[Step 3/5] Generating images and assembling video...")
    try:
        video_path = assemble_video(script, voiceover_path, video_id)
        if video_path:
            results["steps"]["video"] = {"status": "success", "path": video_path}
            file_size = os.path.getsize(video_path) / (1024 * 1024)
            print(f"✓ Video generated: {video_path} ({file_size:.2f} MB)")
        else:
            results["steps"]["video"] = {"status": "failed", "error": "Empty output"}
            print("✗ Video assembly failed")
            return results
    except Exception as e:
        results["steps"]["video"] = {"status": "failed", "error": str(e)}
        print(f"✗ Video assembly failed: {e}")
        return results
    
    print("\n[Step 4/5] Uploading to platforms...")
    try:
        tags = script.get("tags", [])
        upload_results = upload_to_platforms(
            video_path,
            title,
            script.get("narration", ""),
            tags,
            platforms or ["buffer"]
        )
        results["steps"]["upload"] = {"status": "success", "results": upload_results}
        for platform, url in upload_results.items():
            print(f"✓ {platform}: {url}")
    except Exception as e:
        results["steps"]["upload"] = {"status": "failed", "error": str(e)}
        print(f"✗ Upload failed: {e}")
    
    print("\n[Step 5/5] Cleaning up...")
    try:
        cleanup_temp_files(video_id)
        update_topic_status(topic.get("id", ""), "used")
        results["success"] = True
        print("✓ Cleanup completed")
    except Exception as e:
        print(f"✗ Cleanup failed: {e}")
    
    print(f"\n{'='*60}")
    print(f"Video processing completed: {'SUCCESS' if results['success'] else 'FAILED'}")
    print(f"{'='*60}")
    
    return results

def main():
    parser = argparse.ArgumentParser(description="AI自动化视频制作工作流")
    parser.add_argument("--topics", type=int, default=1, help="处理的选题数量")
    parser.add_argument("--platforms", nargs="+", default=["youtube", "tiktok"], 
                        help="目标平台: youtube, tiktok, instagram, buffer")
    parser.add_argument("--topic-id", type=str, default=None, help="指定处理单个选题ID")
    parser.add_argument("--test", action="store_true", help="测试模式（只生成脚本）")
    
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print("  AI自动化视频制作工作流")
    print(f"  日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    if args.test:
        print("\n测试模式: 只生成脚本")
        topics = get_pending_topics(1)
        if topics:
            topic = topics[0]
            script = generate_script(topic)
            print(f"\n生成的脚本:")
            print(json.dumps(script, ensure_ascii=False, indent=2))
        else:
            print("没有待处理的选题")
        return
    
    if args.topic_id:
        topics = load_topic_pool()
        topic = next((t for t in topics if t.get("id") == args.topic_id), None)
        if topic:
            process_topic(topic, args.platforms)
        else:
            print(f"未找到选题ID: {args.topic_id}")
        return
    
    pending_topics = get_pending_topics(args.topics)
    
    if not pending_topics:
        print("没有待处理的选题")
        return
    
    print(f"\n找到 {len(pending_topics)} 个待处理选题")
    
    for topic in pending_topics:
        results = process_topic(topic, args.platforms)
        
        results_path = os.path.join(Config.OUTPUT_DIR, f"{results['video_id']}_results.json")
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()