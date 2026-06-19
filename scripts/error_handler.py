import os
import json
import re
from datetime import datetime
from typing import Dict, List, Any

class ErrorHandler:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.kb_path = os.path.join(repo_path, "config", "error_knowledge_base.json")
        self.load_knowledge_base()
    
    def load_knowledge_base(self):
        if os.path.exists(self.kb_path):
            with open(self.kb_path, 'r', encoding='utf-8') as f:
                self.kb = json.load(f)
        else:
            self.kb = {
                "error_patterns": [],
                "errors": [],
                "resolved_count": 0,
                "total_errors": 0
            }
    
    def save_knowledge_base(self):
        os.makedirs(os.path.dirname(self.kb_path), exist_ok=True)
        with open(self.kb_path, 'w', encoding='utf-8') as f:
            json.dump(self.kb, f, indent=2, ensure_ascii=False)
    
    def classify_error(self, error_message: str) -> str:
        if "failed to unmarshal YAML" in error_message or "yaml: unmarshal errors" in error_message:
            return "yaml_parsing"
        elif "template for shortcode" in error_message and "not found" in error_message:
            return "shortcode_missing"
        elif "cannot unmarshal !!str" in error_message and "into map[string]interface" in error_message:
            return "encoding_corruption"
        elif "timeout" in error_message.lower():
            return "build_timeout"
        elif "failed to push" in error_message or "git push" in error_message.lower():
            return "git_push_failed"
        else:
            return "unknown"
    
    def add_error(self, error_message: str, workflow_name: str, run_id: str, category: str = None):
        if category is None:
            category = self.classify_error(error_message)
        
        category_name_map = {
            "yaml_parsing": "YAML解析错误",
            "shortcode_missing": "短代码缺失",
            "encoding_corruption": "编码损坏",
            "build_timeout": "构建超时",
            "git_push_failed": "Git推送失败",
            "unknown": "未知错误"
        }
        
        error_record = {
            "id": f"err_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "workflow_name": workflow_name,
            "run_id": run_id,
            "category": category,
            "category_name": category_name_map.get(category, "未知错误"),
            "error_message": error_message[:500],
            "status": "pending",
            "attempts": 0
        }
        
        if "errors" not in self.kb:
            self.kb["errors"] = []
        self.kb["errors"].append(error_record)
        self.save_knowledge_base()
        return error_record
    
    def auto_fix(self, error_record: Dict[str, Any]) -> bool:
        category = error_record["category"]
        error_message = error_record["error_message"]
        
        if category == "shortcode_missing":
            shortcode_name = self._extract_shortcode_name(error_message)
            if shortcode_name:
                return self._create_missing_shortcode(shortcode_name)
        
        elif category == "encoding_corruption" or category == "yaml_parsing":
            file_path = self._extract_file_path(error_message)
            if file_path:
                return self._repair_corrupted_file(file_path)
        
        return False
    
    def _extract_shortcode_name(self, error_message: str) -> str:
        match = re.search(r'shortcode "([^"]+)" not found', error_message)
        return match.group(1) if match else None
    
    def _extract_file_path(self, error_message: str) -> str:
        match = re.search(r'"/home/runner/work/[^/]+/[^/]+/([^"]+)"', error_message)
        if match:
            return os.path.join(self.repo_path, match.group(1).replace('/', os.sep))
        return None
    
    def _create_missing_shortcode(self, shortcode_name: str) -> bool:
        shortcode_dir = os.path.join(self.repo_path, "layouts", "shortcodes")
        os.makedirs(shortcode_dir, exist_ok=True)
        
        shortcode_path = os.path.join(shortcode_dir, f"{shortcode_name}.html")
        
        if shortcode_name == "vpn-link":
            template = '<a href="{{ .Site.Params.affiliate.vpn }}" rel="nofollow sponsored" target="_blank" class="affiliate-link">{{- if .Get 0 -}}{{ .Get 0 }}{{- else -}}Get VPN{{- end -}}</a>'
        elif shortcode_name == "esim-link":
            template = '<a href="{{ .Site.Params.affiliate.esim }}" rel="nofollow sponsored" target="_blank" class="affiliate-link">{{- if .Get 0 -}}{{ .Get 0 }}{{- else -}}Get eSIM{{- end -}}</a>'
        elif shortcode_name == "nordpass-link":
            template = '<a href="{{ .Site.Params.affiliate.nordpass }}" rel="nofollow sponsored" target="_blank" class="affiliate-link">{{- if .Get 0 -}}{{ .Get 0 }}{{- else -}}Get NordPass{{- end -}}</a>'
        else:
            template = '{{- .Inner -}}'
        
        with open(shortcode_path, 'w', encoding='utf-8') as f:
            f.write(template)
        
        print(f"Created missing shortcode: {shortcode_name}")
        return True
    
    def _repair_corrupted_file(self, file_path: str) -> bool:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if "-t-i-t-l-e-" in content or "-d-e-s-c-r-i-p-t-i-o-n-" in content:
                os.remove(file_path)
                print(f"Deleted corrupted file: {file_path}")
                return True
        
        return False
    
    def get_pending_errors(self) -> List[Dict[str, Any]]:
        return [e for e in self.kb.get("errors", []) if e.get("status") == "pending"]
    
    def mark_resolved(self, error_id: str):
        for error in self.kb.get("errors", []):
            if error.get("id") == error_id:
                error["status"] = "resolved"
                error["resolved_at"] = datetime.now().isoformat()
                break
        self.save_knowledge_base()
    
    def get_error_summary(self) -> Dict[str, int]:
        summary = {}
        for error in self.kb.get("errors", []):
            category = error.get("category_name", "未知")
            summary[category] = summary.get(category, 0) + 1
        return summary
