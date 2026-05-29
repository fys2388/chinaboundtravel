import os
import glob
import frontmatter

def main():
    posts_dir = "content/posts"
    files = glob.glob(f"{posts_dir}/*.md")
    
    print(f"Checking {len(files)} files...\n")
    
    incomplete = []
    
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
            
            # 检查必需字段
            has_title = 'title' in post.metadata
            has_description = 'description' in post.metadata
            has_date = 'date' in post.metadata
            has_author = 'author' in post.metadata
            has_params = 'params' in post.metadata
            
            params_ok = False
            if has_params:
                params = post.metadata['params']
                has_keywords = isinstance(params, dict) and 'keywords' in params
                has_faq = isinstance(params, dict) and 'faq' in params
                params_ok = has_keywords and has_faq
            
            if not (has_title and has_description and has_date and has_author and has_params and params_ok):
                incomplete.append({
                    'file': os.path.basename(filepath),
                    'title': has_title,
                    'description': has_description,
                    'date': has_date,
                    'author': has_author,
                    'params': has_params,
                    'params_ok': params_ok
                })
        
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
    
    print(f"Files with incomplete front matter: {len(incomplete)}\n")
    for item in incomplete:
        print(f"  - {item['file']}")
        print(f"    Title: {item['title']}, Desc: {item['description']}, Date: {item['date']}, Author: {item['author']}, Params: {item['params']}, Params OK: {item['params_ok']}")
        print()

if __name__ == "__main__":
    main()
