#!/usr/bin/env python3
"""
Script to fix timezone import issues across the codebase.
"""

import os
import re
from pathlib import Path

def fix_timezone_import(file_path: str) -> bool:
    """Fix timezone import issues in a file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Check if file uses timezone.utc but doesn't import timezone
        if 'timezone.utc' in content and 'from datetime import' in content:
            # Check if timezone is already imported
            if 'timezone' not in content:
                # Add timezone to the import
                content = re.sub(
                    r'from datetime import ([^\\n]+)',
                    r'from datetime import \1, timezone',
                    content
                )
        
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"✅ Fixed timezone import in {file_path}")
            return True
        else:
            print(f"⏭️  No timezone import fix needed in {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")
        return False

def main():
    """Main function to fix timezone imports."""
    print("🛡️  Starting timezone import fixes...")
    
    # Find all Python files in the app directory
    app_dir = Path("app")
    python_files = list(app_dir.rglob("*.py"))
    
    fixes = 0
    
    for file_path in python_files:
        file_str = str(file_path)
        
        # Skip __pycache__ and test files
        if "__pycache__" in file_str or "test_" in file_str:
            continue
        
        print(f"\n📁 Processing {file_str}...")
        
        # Fix timezone imports
        if fix_timezone_import(file_str):
            fixes += 1
    
    print(f"\n🎉 Timezone import fixes complete!")
    print(f"   🔧 Fixed {fixes} files with timezone imports")
    print(f"   📊 Total files processed: {len(python_files)}")

if __name__ == "__main__":
    main()
