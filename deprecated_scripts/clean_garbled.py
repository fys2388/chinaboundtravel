import glob

def clean_file(filepath):
    with open(filepath, 'rb') as f:
        content = f.read()
    
    text = content.decode('utf-8', errors='replace')
    
    garbled_chars = [
        '\u9910', '\u613f', '\u9280', '\u53c8', '\u949d', '\u203f',
        '\u6f5c', '\u6839', '\u53e4', '\u95e8', '\u5bb6', '\u5c0e',
        '\u7426', '\u4e0a', '\u56ed', '\u9ec3', '\u6c99', '\u5317',
        '\u8def', '\u70e6', '\u5c0f', '\u9f8d', '\u5b9a', '\u6cd5',
        '\u79c1', '\u5229', '\u6dee', '\u6c34', '\u4e2d', '\u65b0',
        '\u5929', '\u5730', '\u7530', '\u5b50', '\u6b66', '\u5eb7',
        '\u660e', '\u661f', '\u5927', '\u4e16', '\u754c', '\u5e08',
        '\u82b1', '\u591a', '\u5c11', '\u91d1', '\u4e0d', '\u8981',
        '\u8fa3', '\u8bdd', '\u9501', '\u539f', '\u5e9c', '\u79df',
        '\u5c42', '\u5f3a', '\u5408', '\u95ee', '\u7b54', '\u5f69',
        '\u6c11', '\u653f', '\u5e9c', '\u90fd', '\u6709', '\u5f88',
        '\u597d', '\u7684', '\u8d77', '\u70b9', '\u6bcf', '\u4e2a',
        '\u90fd', '\u63d0', '\u4f9b', '\u4e0d', '\u540c', '\u7684',
        '\u4f53', '\u9a8c', '\u4ece', '\u5386', '\u53f2', '\u5230',
        '\u98df', '\u7269', '\u5230', '\u718a', '\u72f8', '\u53ef',
        '\u4ee5', '\u4f7f', '\u7528', '\u4e0b', '\u9762', '\u7684',
        '\u4e2d', '\u6587', '\u6765', '\u8bf4', '\u660e', '\u4e8e',
        '\u4ec0', '\u4e48', '\u4eba', '\u4eec', '\u5e94', '\u8be5',
        '\u8bbf', '\u95ee', '\u4ec0', '\u4e48', '\u57ce', '\u5e02',
        '\u4e2d', '\u56fd', '\u7684', '\u57ce', '\u5e02', '\u5f88',
        '\u591a', '\u5730', '\u65b9', '\u7684', '\u4ea4', '\u901a',
        '\u7cfb', '\u7edf', '\u90fd', '\u5f88', '\u4e0d', '\u9519',
        '\u53ef', '\u4ee5', '\u4f7f', '\u7528', '\u4ee3', '\u5238',
        '\u6216', '\u8005', '\u8f66', '\u8f7d', '\u547c', '\u53eb',
        '\u5e94', '\u7528', '\u90fd', '\u5f88', '\u4fbf', '\u4fbf',
        '\u6613', '\u4f7f', '\u7528', '\u4e86', '\u8fd9', '\u4e2a',
        '\u6587', '\u4ef6', '\u662f', '\u4e2d', '\u6587', '\u7684',
        '\u56e0', '\u4e3a', '\u6211', '\u4eec', '\u6b63', '\u5728',
        '\u8ba9', '\u4e2d', '\u56fd', '\u7684', '\u65c5', '\u6e38',
        '\u8005', '\u4eec', '\u80fd', '\u591f', '\u66f4', '\u597d',
        '\u5730', '\u4e86', '\u89e3', '\u8fd9', '\u4e2a', '\u57ce',
        '\u5e02', '\u7684', '\u6587', '\u5316', '\u548c', '\u7f8e',
        '\u98ce', '\u8fd9', '\u4e9b', '\u5185', '\u5bb9', '\u90fd',
        '\u5f88', '\u6709', '\u610f', '\u4e49', '\u540c', '\u65f6',
        '\u4e5f', '\u80fd', '\u591f', '\u8ba9', '\u60a8', '\u7684',
        '\u65c5', '\u6e38', '\u66f4', '\u52a0', '\u6709', '\u8da3',
        '\u8fd9', '\u662f', '\u4e00', '\u4e2a', '\u5f88', '\u597d',
        '\u7684', '\u5f00', '\u59cb', '\u4f60', '\u53ef', '\u4ee5',
        '\u4ece', '\u8fd9', '\u4e2a', '\u57ce', '\u5e02', '\u5f00',
        '\u59cb', '\u4f60', '\u7684', '\u4e2d', '\u56fd', '\u65c5',
        '\u6e38', '\u4e4b', '\u65c5', '\u6211', '\u4eec', '\u5e0c',
        '\u671b', '\u8fd9', '\u4e2a', '\u6587', '\u4ef6', '\u80fd',
        '\u591f', '\u5e2e', '\u52a9', '\u4f60', '\u66f4', '\u597d',
        '\u5730', '\u8fdb', '\u884c', '\u4e2d', '\u56fd', '\u65c5',
        '\u6e38', '\u5982', '\u679c', '\u4f60', '\u6709', '\u4efb',
        '\u4f55', '\u95ee', '\u9898', '\u6216', '\u8005', '\u5efa',
        '\u8bae', '\u90fd', '\u53ef', '\u4ee5', '\u8054', '\u7cfb',
        '\u6211', '\u4eec', '\u6211', '\u4eec', '\u4f1a', '\u5c3d',
        '\u91cf', '\u5e2e', '\u52a9', '\u4f60', '\u7684', '\u8fd9',
        '\u4e2a', '\u6587', '\u4ef6', '\u662f', '\u7531', '\u4e2d',
        '\u56fd', '\u65c5', '\u6e38', '\u54a8', '\u8be2', '\u4e2d',
        '\u5fc3', '\u5f00', '\u53d1', '\u7684', '\u4e13', '\u4e1a',
        '\u56e2', '\u961f', '\u7f16', '\u5199', '\u7684', '\u4e13',
        '\u95e8', '\u4e3a', '\u56fd', '\u5916', '\u65c5', '\u6e38',
        '\u8005', '\u63d0', '\u4f9b', '\u7684', '\u4e13', '\u4e1a',
        '\u65c5', '\u6e38', '\u6307', '\u5357', '\u6211', '\u4eec',
        '\u7684', '\u76ee', '\u6807', '\u662f', '\u8ba9', '\u6bcf',
        '\u4e2a', '\u56fd', '\u5916', '\u65c5', '\u6e38', '\u8005',
        '\u90fd', '\u80fd', '\u591f', '\u6709', '\u6548', '\u5730',
        '\u8fdb', '\u884c', '\u4e2d', '\u56fd', '\u65c5', '\u6e38',
        '\u8fd9', '\u4e2a', '\u6587', '\u4ef6', '\u5305', '\u542b',
        '\u4e86', '\u5f88', '\u591a', '\u6709', '\u7528', '\u7684',
        '\u4fe1', '\u606f', '\u5305', '\u62ec', '\u4e2d', '\u56fd',
        '\u5404', '\u57ce', '\u5e02', '\u7684', '\u65c5', '\u6e38',
        '\u6307', '\u5357', '\u5305', '\u62ec', '\u5357', '\u4eac',
        '\u4e0a', '\u6d77', '\u6210', '\u90fd', '\u897f', '\u5b89',
        '\u7b49', '\u91cd', '\u8981', '\u65c5', '\u6e38', '\u57ce',
        '\u5e02', '\u8fd9', '\u4e9b', '\u57ce', '\u5e02', '\u7684',
        '\u4e3b', '\u8981', '\u65c5', '\u6e38', '\u666f', '\u70b9',
        '\u3001', '\u4ea4', '\u901a', '\u65b9', '\u5f0f', '\u3001',
        '\u4f4f', '\u5bbf', '\u65b9', '\u5f0f', '\u3001', '\u98df',
        '\u98df', '\u3001', '\u8d39', '\u7528', '\u7b49', '\u7b49',
        '\u7b49', '\u8fd9', '\u4e2a', '\u6587', '\u4ef6', '\u8fd8',
        '\u5305', '\u542b', '\u4e86', '\u4e00', '\u4e9b', '\u65c5',
        '\u6e38', '\u63d0', '\u793a', '\u548c', '\u5efa', '\u8bae',
        '\u5e2e', '\u52a9', '\u4f60', '\u66f4', '\u597d', '\u5730',
        '\u8fdb', '\u884c', '\u4e2d', '\u56fd', '\u65c5', '\u6e38',
        '\u5982', '\u679c', '\u4f60', '\u8fd8', '\u6709', '\u4efb',
        '\u4f55', '\u95ee', '\u9898', '\u6216', '\u8005', '\u5efa',
        '\u8bae', '\u90fd', '\u53ef', '\u4ee5', '\u8054', '\u7cfb',
        '\u6211', '\u4eec', '\u6211', '\u4eec', '\u4f1a', '\u5c3d',
        '\u91cf', '\u5e2e', '\u52a9', '\u4f60', '\u7684', '\u8fd9',
        '\u4e2a', '\u6587', '\u4ef6', '\u662f', '\u7531', '\u4e2d',
        '\u56fd', '\u65c5', '\u6e38', '\u54a8', '\u8be2', '\u4e2d',
        '\u5fc3', '\u5f00', '\u53d1', '\u7684', '\u4e13', '\u4e1a',
        '\u56e2', '\u961f', '\u7f16', '\u5199', '\u7684', '\u4e13',
        '\u95e8', '\u4e3a', '\u56fd', '\u5916', '\u65c5', '\u6e38',
        '\u8005', '\u63d0', '\u4f9b', '\u7684', '\u4e13', '\u4e1a',
        '\u65c5', '\u6e38', '\u6307', '\u5357', '\u6211', '\u4eec',
        '\u7684', '\u76ee', '\u6807', '\u662f', '\u8ba9', '\u6bcf',
        '\u4e2a', '\u56fd', '\u5916', '\u65c5', '\u6e38', '\u8005',
        '\u90fd', '\u80fd', '\u591f', '\u6709', '\u6548', '\u5730',
        '\u8fdb', '\u884c', '\u4e2d', '\u56fd', '\u65c5', '\u6e38',
    ]
    
    original_length = len(text)
    for char in garbled_chars:
        text = text.replace(char, '')
    
    if len(text) != original_length:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"Cleaned: {filepath} (removed {original_length - len(text)} chars)")
        return True
    return False

def main():
    md_files = glob.glob("content/**/*.md", recursive=True)
    cleaned_count = 0
    
    for filepath in md_files:
        if clean_file(filepath):
            cleaned_count += 1
    
    print(f"\nDone! Cleaned {cleaned_count} files")

if __name__ == "__main__":
    main()
