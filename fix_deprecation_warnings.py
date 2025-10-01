#!/usr/bin/env python3
"""
Script to fix deprecation warnings across the codebase.
This script will update datetime.utcnow() calls and Pydantic V1 syntax.
"""

import os
import re
from pathlib import Path

def fix_datetime_utcnow(file_path: str) -> bool:
    """Fix datetime.utcnow() calls in a file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Replace datetime.utcnow() with datetime.now(timezone.utc)
        content = re.sub(
            r'datetime\.utcnow\(\)',
            'datetime.now(timezone.utc)',
            content
        )
        
        # Add timezone import if needed
        if 'datetime.now(timezone.utc)' in content and 'from datetime import' in content:
            # Check if timezone is already imported
            if 'timezone' not in content:
                content = re.sub(
                    r'from datetime import ([^\\n]+)',
                    r'from datetime import \1, timezone',
                    content
                )
        
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"✅ Fixed datetime.utcnow() in {file_path}")
            return True
        else:
            print(f"⏭️  No datetime.utcnow() found in {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")
        return False

def fix_pydantic_validator(file_path: str) -> bool:
    """Fix Pydantic V1 validator syntax."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_content = content
        changes_made = False
        
        # Replace @validator with @field_validator
        if '@validator(' in content:
            content = re.sub(
                r'@validator\(([^)]+)\)',
                r'@field_validator(\1)',
                content
            )
            changes_made = True
        
        # Replace .dict() with .model_dump()
        if '.dict()' in content:
            content = content.replace('.dict()', '.model_dump()')
            changes_made = True
        
        # Add field_validator import if needed
        if '@field_validator(' in content and 'field_validator' not in content:
            if 'from pydantic import' in content:
                content = re.sub(
                    r'from pydantic import ([^\\n]+)',
                    r'from pydantic import \1, field_validator',
                    content
                )
                changes_made = True
        
        if changes_made:
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"✅ Fixed Pydantic syntax in {file_path}")
            return True
        else:
            print(f"⏭️  No Pydantic fixes needed in {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")
        return False

def main():
    """Main function to fix deprecation warnings."""
    print("🛡️  Starting deprecation warning fixes...")
    
    # Find all Python files in the app directory
    app_dir = Path("app")
    python_files = list(app_dir.rglob("*.py"))
    
    datetime_fixes = 0
    pydantic_fixes = 0
    
    for file_path in python_files:
        file_str = str(file_path)
        
        # Skip __pycache__ and test files
        if "__pycache__" in file_str or "test_" in file_str:
            continue
        
        print(f"\n📁 Processing {file_str}...")
        
        # Fix datetime.utcnow() calls
        if fix_datetime_utcnow(file_str):
            datetime_fixes += 1
        
        # Fix Pydantic syntax
        if fix_pydantic_validator(file_str):
            pydantic_fixes += 1
    
    print(f"\n🎉 Deprecation fixes complete!")
    print(f"   📅 Fixed {datetime_fixes} files with datetime.utcnow()")
    print(f"   🔧 Fixed {pydantic_fixes} files with Pydantic syntax")
    print(f"   📊 Total files processed: {len(python_files)}")

if __name__ == "__main__":
    main()
