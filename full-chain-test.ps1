$env:DEEPSEEK_API_KEY="***REMOVED***"
$env:DEEPSEEK_BACKUP_API_KEY="***REMOVED***"
$env:FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/***REMOVED***"
$env:GEMINI_API_KEY=""

Write-Host "=== 开始全链路测试 ==="
Write-Host "1. 生成文章..."

cd e:\AI\dulizhan\travel-blog
python chinaboundtravel_social_bot/joran_blog_generator.py