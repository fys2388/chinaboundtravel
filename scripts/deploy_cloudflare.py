import os
import json
import subprocess

def deploy_to_cloudflare():
    print("=== Cloudflare Pages Deployment Script ===")
    
    CLOUDFLARE_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN")
    CLOUDFLARE_ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    PROJECT_NAME = "chinaboundtravel"
    
    if not CLOUDFLARE_API_TOKEN or not CLOUDFLARE_ACCOUNT_ID:
        print("❌ Missing CLOUDFLARE_API_TOKEN or CLOUDFLARE_ACCOUNT_ID")
        print("Please set these environment variables first.")
        return False
    
    print("✅ Environment variables configured")
    
    print("\n=== Building site ===")
    result = subprocess.run(["hugo", "--gc", "--minify"], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Build failed: {result.stderr}")
        return False
    print("✅ Site built successfully")
    
    print("\n=== Deploying to Cloudflare Pages ===")
    result = subprocess.run(
        ["npx", "cloudflare", "pages", "deploy", "public", "--project-name", PROJECT_NAME],
        capture_output=True,
        text=True,
        env={**os.environ, "CLOUDFLARE_API_TOKEN": CLOUDFLARE_API_TOKEN}
    )
    
    if result.returncode == 0:
        print("✅ Deployment successful!")
        print(result.stdout)
        return True
    else:
        print(f"❌ Deployment failed: {result.stderr}")
        return False

if __name__ == "__main__":
    deploy_to_cloudflare()
