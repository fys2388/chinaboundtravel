#!/usr/bin/env python3
import os
import sys
import json
import subprocess
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.error_handler import ErrorHandler

def run_hugo_build(repo_path: str) -> str:
    """运行 Hugo 构建并返回输出"""
    try:
        result = subprocess.run(
            ["hugo", "--gc", "--minify"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.stdout + result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "Build timed out", 1
    except Exception as e:
        return str(e), 1

def auto_fix_build_errors(repo_path: str) -> bool:
    """自动检测并修复构建错误"""
    error_handler = ErrorHandler(repo_path)
    
    build_output, exit_code = run_hugo_build(repo_path)
    
    if exit_code == 0:
        print("✅ Hugo build succeeded!")
        return True
    
    print("❌ Hugo build failed, attempting auto-fix...")
    print(f"Build output:\n{build_output}")
    
    error_record = error_handler.add_error(
        build_output,
        workflow_name="auto-fix",
        run_id="manual"
    )
    
    fixed = error_handler.auto_fix(error_record)
    
    if fixed:
        print("✅ Auto-fix applied, retrying build...")
        build_output, exit_code = run_hugo_build(repo_path)
        
        if exit_code == 0:
            print("✅ Build succeeded after auto-fix!")
            error_handler.mark_resolved(error_record["id"])
            return True
        else:
            print(f"❌ Build still failing: {build_output}")
            return False
    else:
        print("❌ No auto-fix available for this error")
        return False

def push_changes(repo_path: str, commit_message: str = "auto-fix: resolve build errors") -> bool:
    """推送修复到远程仓库"""
    try:
        subprocess.run(["git", "add", "-A"], cwd=repo_path, check=True)
        subprocess.run(["git", "commit", "-m", commit_message], cwd=repo_path, check=True)
        subprocess.run(["git", "push"], cwd=repo_path, check=True)
        print("✅ Changes pushed to remote")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Git push failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Auto-fix Hugo build errors")
    parser.add_argument("--push", action="store_true", help="Push changes after fixing")
    args = parser.parse_args()
    
    repo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    print(f"📁 Repository path: {repo_path}")
    
    success = auto_fix_build_errors(repo_path)
    
    if success and args.push:
        push_changes(repo_path)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
