#!/usr/bin/env python3
"""
测试豆包 Ark 模型代替 DeepSeek 进行博文生成
"""

import os
import sys

# 设置环境变量使用豆包 Ark
os.environ["USE_DOUBAO_ARK"] = "true"

# 导入必要的模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "chinaboundtravel_social_bot"))

from joran_blog_generator import AIEngine

def test_article_generation():
    """测试使用豆包 Ark 生成文章"""
    print("🚀 开始测试豆包 Ark 博文生成...")
    
    try:
        # 创建 AI 引擎（应该自动使用豆包 Ark）
        ai_engine = AIEngine()
        
        if ai_engine.use_doubao:
            print("✅ 成功加载豆包 Ark 模型")
        else:
            print("❌ 未能加载豆包 Ark 模型")
            return
        
        # 测试生成文章
        print("\n📝 开始生成测试文章...")
        topic = "Chengdu food guide"
        geo_region = "US"
        
        # 生成文章
        content = ai_engine.generate_post(topic, geo_region)
        
        print("\n✅ 文章生成成功！")
        print("="*60)
        print(content[:1000] + "..." if len(content) > 1000 else content)
        print("="*60)
        print(f"\n📊 文章长度: {len(content)} 字符")
        
        # 检查是否包含图片占位符
        if "[Image:" in content:
            print("✅ 文章包含图片占位符")
        else:
            print("❌ 文章缺少图片占位符")
            
        # 检查是否包含二级标题
        if "## " in content:
            print("✅ 文章包含二级标题")
        else:
            print("❌ 文章缺少二级标题")
            
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_article_generation()