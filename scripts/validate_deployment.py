import os
import sys
import subprocess
import json

sys.stdout.reconfigure(encoding='utf-8')

def run_command(cmd, cwd=None):
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=300)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"

def validate_hugo_build():
    print("=== Validating Hugo build ===")
    code, stdout, stderr = run_command("hugo --gc --minify", cwd="e:/AI/dulizhan/travel-blog")
    if code != 0:
        print(f"ERROR: Hugo build failed: {stderr}")
        return False
    print("OK: Hugo build successful")
    return True

def validate_yaml_files():
    print("\n=== Validating YAML files ===")
    import yaml
    import glob
    
    errors = []
    yaml_files = glob.glob("content/**/*.md", recursive=True)
    
    for filepath in yaml_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.startswith('---'):
                    end_idx = content.find('\n---\n')
                    if end_idx != -1:
                        frontmatter = content[4:end_idx]
                        yaml.safe_load(frontmatter)
        except Exception as e:
            errors.append(f"{filepath}: {str(e)}")
    
    if errors:
        print("ERROR: YAML validation failed:")
        for error in errors:
            print(f"  - {error}")
        return False
    print("OK: YAML files valid")
    return True

def validate_workflows():
    print("\n=== Validating workflow files ===")
    workflows = [
        ".github/workflows/deploy-cloudflare-pages.yml",
        ".github/workflows/deploy.yml",
        ".github/workflows/daily-inspection.yml"
    ]
    
    for workflow in workflows:
        if not os.path.exists(workflow):
            print(f"ERROR: Missing workflow: {workflow}")
            return False
    print("OK: Workflow files exist")
    return True

def validate_secrets():
    print("\n=== Checking required secrets ===")
    required_secrets = [
        "CLOUDFLARE_API_TOKEN",
        "CLOUDFLARE_ACCOUNT_ID",
        "CHINABOUND",
        "FEISHU_WEBHOOK_URL"
    ]
    
    print(f"Required secrets: {', '.join(required_secrets)}")
    print("Please verify these are configured in GitHub Secrets")
    return True

def main():
    print("=== Running deployment validation ===\n")
    
    checks = [
        ("Hugo Build", validate_hugo_build),
        ("YAML Validation", validate_yaml_files),
        ("Workflow Files", validate_workflows),
        ("Secrets Check", validate_secrets)
    ]
    
    all_passed = True
    for name, check in checks:
        try:
            if not check():
                all_passed = False
        except Exception as e:
            print(f"ERROR: {name} failed with exception: {e}")
            all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("SUCCESS: All validations passed! Ready for deployment.")
        return 0
    else:
        print("FAILURE: Some validations failed. Please fix before deployment.")
        return 1

if __name__ == "__main__":
    sys.exit(main())