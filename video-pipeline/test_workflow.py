#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试AI自动化视频制作工作流各模块
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

print("=" * 60)
print("AI自动化视频制作工作流 - 模块测试")
print("=" * 60)

modules = [
    ("config", "Config"),
    ("script_generator", "generate_script, get_pending_topics, load_topic_pool"),
    ("voiceover", "generate_voiceover, synthesize_speech"),
    ("video_assembler", "assemble_video, generate_image, create_slide"),
    ("uploader", "upload_to_platforms, YouTubeUploader, TikTokUploader"),
]

success_count = 0
fail_count = 0

for module_name, exports in modules:
    try:
        module = __import__(module_name)
        print(f"\n✓ {module_name}: 导入成功")
        
        export_list = [e.strip() for e in exports.split(",")]
        for export in export_list:
            if hasattr(module, export):
                print(f"  - {export}: OK")
            else:
                print(f"  - {export}: MISSING")
                fail_count += 1
        success_count += 1
    except Exception as e:
        print(f"\n✗ {module_name}: 导入失败 - {e}")
        fail_count += 1

print(f"\n{'='*60}")
print(f"测试结果: {success_count} 成功, {fail_count} 失败")

if fail_count == 0:
    print("所有模块测试通过!")
    print("\n工作流文件结构:")
    for f in sorted(os.listdir(os.path.dirname(__file__))):
        if f.endswith(".py"):
            size = os.path.getsize(os.path.join(os.path.dirname(__file__), f))
            print(f"  - {f} ({size} bytes)")
else:
    print("部分模块存在问题，请检查错误信息")