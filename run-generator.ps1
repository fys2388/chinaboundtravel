cd e:\AI\dulizhan\travel-blog
$env:DEEPSEEK_API_KEY="***REMOVED***"
$env:DEEPSEEK_BACKUP_API_KEY="***REMOVED***"
$env:FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/***REMOVED***"

Write-Host "=== 开始生成文章 ==="
python chinaboundtravel_social_bot/joran_blog_generator.py