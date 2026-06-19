import os
import glob

def main():
    posts_dir = "content"
    files = glob.glob(f"{posts_dir}/**/*.md", recursive=True)
    
    garbled_chars = ["馃", "彲", "镒", "镟", "镞", "镙", "镠", "镡", "镢", "镣", "镤", "镥", "镦", "镧", "镨", "镩", "镪", "镫", "镬", "镮", "镲", "镳", "镴", "镵", "長", "镸", "镹", "镺", "镻", "镼", "镽", "镾", "长", "锕", "锖", "锗", "锘", "锝", "锞", "锟", "锠", "锢", "锣", "锤", "锥", "锦", "锧", "锨", "锩", "锪", "锫", "锬", "锭", "键", "锯", "锰", "锱", "锲", "锴", "锶", "锼", "锽", "锾", "锿", "镃", "镄", "镅", "镆", "镈", "镋", "镌", "镍", "镎", "镏", "镕", "彊", "锔", "搷", "寙", "惣", "徍", "棑", "攋", "鈥"]
    
    print(f"Checking {len(files)} files...\n")
    
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            has_garbled = False
            for char in garbled_chars:
                if char in content:
                    has_garbled = True
                    break
            
            if has_garbled:
                print(f"⚠️  {filepath}")
        except Exception as e:
            pass

if __name__ == "__main__":
    main()
