#!/usr/bin/env python3
"""Fix mojibake characters in UI source files."""
import os

BASE_DIR = r'd:\SKILL_UP\TEST_APPS\Directory_analysis\ui'

# Map of broken sequences to their proper Unicode characters
# These are Windows-1252 Latin-1 misinterpretations of UTF-8 characters
REPLACEMENTS = {
    # The em-dash was encoded as 0xE2 0x80 0x94 (UTF-8) but read as Latin-1,
    # giving the three characters: â, €, " (which visually appears as â€")
    # However, in the actual file they appear as the literal characters "â€" 
    # So we replace the literal string "â€" with "—"
    "â€": "—",       # em-dash
    "â€¦": "…",       # horizontal ellipsis
}

def fix_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    for old, new in REPLACEMENTS.items():
        content = content.replace(old, new)
    
    if content != original:
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(content)
        return True
    return False

def main():
    fixed = []
    for root, dirs, files in os.walk(BASE_DIR):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                if fix_file(path):
                    fixed.append(path)
                    print(f"Fixed: {path}")
    
    if not fixed:
        print("No changes needed.")
    else:
        print(f"\nFixed {len(fixed)} file(s).")

if __name__ == '__main__':
    main()