import os

def replace_in_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        return # Skip binary
        
    updated = False
    
    if 'TradingHelper' in content:
        content = content.replace('TradingHelper', 'TradeSentinel')
        updated = True
        
    if filepath.endswith('index.html'):
        if 'href="/vite.svg"' in content or 'type="image/svg+xml"' in content:
            content = content.replace('type="image/svg+xml"', 'type="image/png"')
            content = content.replace('href="/vite.svg"', 'href="/logo.png"')
            updated = True
            
    if updated:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filepath}")

for root, _, files in os.walk('.'):
    for f in files:
        # Ignore binary or large hidden directories
        if any(ignored in root for ignored in ['.git', 'node_modules', '__pycache__', 'venv', '.venv']):
            continue
        if f.endswith('.png') or f.endswith('.jpg') or f.endswith('.ico') or f.endswith('.db'):
            continue
        replace_in_file(os.path.join(root, f))
