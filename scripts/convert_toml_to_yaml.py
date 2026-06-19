import os
import re

def convert_toml_to_yaml(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    if not content.startswith('+++'):
        return False
    
    parts = content.split('+++', 2)
    if len(parts) < 3:
        return False
    
    toml_frontmatter = parts[1].strip()
    body = parts[2].lstrip()
    
    yaml_lines = ['---']
    
    for line in toml_frontmatter.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        if '=' in line:
            key, value = line.split('=', 1)
            key = key.strip()
            
            value = value.strip()
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
                yaml_lines.append(f'{key}: "{value}"')
            elif value.startswith('[') and value.endswith(']'):
                items = re.findall(r'"([^"]+)"', value)
                if items:
                    yaml_lines.append(f'{key}:')
                    for item in items:
                        yaml_lines.append(f'  - {item}')
                else:
                    yaml_lines.append(f'{key}: []')
            elif value == 'false':
                yaml_lines.append(f'{key}: false')
            elif value == 'true':
                yaml_lines.append(f'{key}: true')
            elif value.isdigit():
                yaml_lines.append(f'{key}: {value}')
            else:
                yaml_lines.append(f'{key}: "{value}"')
    
    yaml_lines.append('---')
    yaml_lines.append('')
    yaml_lines.append(body)
    
    new_content = '\n'.join(yaml_lines)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return True

def main():
    posts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'content', 'posts')
    
    converted_count = 0
    for filename in os.listdir(posts_dir):
        if filename.endswith('.md') and not filename.startswith('.'):
            file_path = os.path.join(posts_dir, filename)
            if convert_toml_to_yaml(file_path):
                print(f"Converted: {filename}")
                converted_count += 1
    
    print(f"\nTotal converted: {converted_count} files")

if __name__ == "__main__":
    main()
