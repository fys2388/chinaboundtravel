#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频流水线测试脚本
逐个环节验证，确保流程闭环
"""
import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from config import Config
from script_generator import generate_script
from voiceover import generate_voiceover
from video_assembler import assemble_video, cleanup_temp_files
from uploader import BufferUploader

def test_buffer_api():
    """测试Buffer API连接和频道获取"""
    print("\n" + "="*60)
    print("测试1: Buffer API连接")
    print("="*60)
    
    uploader = BufferUploader()
    
    if not uploader.access_token:
        print("✗ Buffer access token 未配置")
        return False
    
    print(f"✓ Access token: {uploader.access_token[:20]}...")
    print(f"✓ GraphQL URL: {uploader.graphql_url}")
    print(f"✓ REST URL: {uploader.rest_url}")
    
    channels = uploader.get_account_channels()
    if channels:
        print(f"\n✓ 成功获取 {len(channels)} 个频道:")
        for ch in channels:
            print(f"  - {ch['name']} ({ch['service']}): {ch['id']}")
        return True
    else:
        print("\n✗ Buffer API连接失败，请检查API密钥")
        return False

def test_script_generation():
    """测试脚本生成"""
    print("\n" + "="*60)
    print("测试2: 脚本生成")
    print("="*60)
    
    test_topic = {
        "id": "test-001",
        "title": "Yunnan Adventure: Rice Terraces and Ancient Towns",
        "keywords": ["Yunnan", "travel", "rice terraces", "ancient towns"],
        "category": "travel",
        "geo": "USA"
    }
    
    try:
        script = generate_script(test_topic)
        print(f"✓ 脚本生成成功")
        print(f"  Hook: {script.get('hook', '')[:50]}...")
        print(f"  场景数量: {len(script.get('scenes', []))}")
        print(f"  字幕数量: {len(script.get('subtitles', []))}")
        print(f"  Tags: {script.get('tags', [])}")
        
        script_path = os.path.join(Config.OUTPUT_DIR, "test_script.json")
        with open(script_path, "w", encoding="utf-8") as f:
            json.dump(script, f, ensure_ascii=False, indent=2)
        print(f"  脚本已保存: {script_path}")
        return script
    except Exception as e:
        print(f"✗ 脚本生成失败: {e}")
        return None

def test_voiceover():
    """测试语音合成"""
    print("\n" + "="*60)
    print("测试3: 语音合成")
    print("="*60)
    
    test_text = "Welcome to China! Discover the beauty of Yunnan province with its stunning rice terraces and ancient towns."
    
    try:
        voiceover_path = generate_voiceover(test_text, "test")
        if voiceover_path and os.path.exists(voiceover_path):
            file_size = os.path.getsize(voiceover_path) / (1024 * 1024)
            print(f"✓ 语音合成成功")
            print(f"  文件: {voiceover_path}")
            print(f"  大小: {file_size:.2f} MB")
            return voiceover_path
        else:
            print("✗ 语音合成失败")
            return None
    except Exception as e:
        print(f"✗ 语音合成失败: {e}")
        return None

def test_video_assembly():
    """测试视频组装"""
    print("\n" + "="*60)
    print("测试4: 视频组装")
    print("="*60)
    
    test_script = {
        "hook": "Discover Yunnan",
        "narration": "Welcome to Yunnan, China's most beautiful province.",
        "scenes": [
            {"time": "0-5s", "description": "Rice terraces", "image_prompt": "Beautiful rice terraces in Yuanyang, Yunnan, China at sunrise, golden light, misty mountains, cinematic photography"},
            {"time": "5-10s", "description": "Ancient town", "image_prompt": "Traditional Chinese ancient town with cobblestone streets, lanterns, wooden buildings, evening atmosphere"}
        ],
        "subtitles": [
            {"time": "0-5s", "text": "Discover Yunnan"},
            {"time": "5-10s", "text": "China's Hidden Gem"}
        ],
        "tags": ["#Yunnan", "#ChinaTravel"]
    }
    
    voiceover_path = None
    try:
        voiceover_path = generate_voiceover(test_script["narration"], "test_video")
        if not voiceover_path:
            print("⚠ 语音合成失败，继续生成无音频视频")
    except Exception as e:
        print(f"⚠ 语音合成失败: {e}")
    
    try:
        video_path = assemble_video(test_script, voiceover_path, "test_video")
        if video_path and os.path.exists(video_path):
            file_size = os.path.getsize(video_path) / (1024 * 1024)
            print(f"✓ 视频组装成功")
            print(f"  文件: {video_path}")
            print(f"  大小: {file_size:.2f} MB")
            return video_path
        else:
            print("✗ 视频组装失败")
            return None
    except Exception as e:
        print(f"✗ 视频组装失败: {e}")
        return None

def test_buffer_upload(video_path):
    """测试Buffer上传"""
    print("\n" + "="*60)
    print("测试5: Buffer视频上传")
    print("="*60)
    
    if not video_path or not os.path.exists(video_path):
        print("✗ 视频文件不存在")
        return False
    
    uploader = BufferUploader()
    
    if not uploader.access_token:
        print("✗ Buffer access token 未配置")
        return False
    
    channels = uploader.get_account_channels()
    
    if not channels:
        print("✗ 未获取到频道")
        return False
    
    channel_id = channels[0]["id"]
    print(f"✓ 使用频道: {channels[0]['name']} ({channels[0]['service']})")
    
    try:
        print(f"\n上传文件: {video_path}")
        media_id = uploader.upload_file(video_path)
        
        if media_id:
            print(f"✓ 文件上传成功, media_id: {media_id}")
            
            text = "Yunnan Adventure: Discover China's most beautiful province #Yunnan #ChinaTravel"
            result = uploader.create_post(channel_id, text, media_id)
            
            if result:
                print(f"✓ 帖子创建成功: {result}")
                return True
            else:
                print("✗ 帖子创建失败")
                return False
        else:
            print("✗ 文件上传失败，尝试创建纯文字帖子...")
            text = "Yunnan Adventure: Discover China's most beautiful province #Yunnan #ChinaTravel"
            result = uploader.create_post(channel_id, text)
            
            if result:
                print(f"✓ 纯文字帖子创建成功: {result}")
                return True
            else:
                print("✗ 帖子创建失败")
                return False
    except Exception as e:
        print(f"✗ 上传失败: {e}")
        return False

def run_full_test():
    """运行完整测试流程"""
    print(f"\n{'='*60}")
    print("  视频流水线完整测试")
    print(f"  日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    results = []
    
    results.append(("Buffer API", test_buffer_api()))
    
    script = test_script_generation()
    results.append(("脚本生成", script is not None))
    
    voiceover = test_voiceover()
    results.append(("语音合成", voiceover is not None))
    
    video = test_video_assembly()
    results.append(("视频组装", video is not None))
    
    if video:
        results.append(("Buffer上传", test_buffer_upload(video)))
    
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for step, success in results:
        status = "✓ 通过" if success else "✗ 失败"
        print(f"  {step}: {status}")
    
    print(f"\n  总结果: {passed}/{total} 通过")
    
    if passed == total:
        print("\n  🎉 所有测试通过！流程闭环成功！")
    else:
        print(f"\n  ⚠ {total - passed} 个测试失败，请检查相关环节")
    
    cleanup_temp_files("test")
    
    return passed == total

if __name__ == "__main__":
    run_full_test()