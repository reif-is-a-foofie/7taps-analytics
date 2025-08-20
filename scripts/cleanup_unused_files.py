#!/usr/bin/env python3
"""
Cleanup script to identify and remove unused files from the 7taps analytics codebase.
This script analyzes imports and usage to determine which files are actually needed.
"""

import os
import re
import shutil
from pathlib import Path
from typing import Set, Dict, List

def get_all_python_files(directory: str) -> List[str]:
    """Get all Python files in the directory recursively."""
    python_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

def extract_imports(file_path: str) -> Set[str]:
    """Extract all import statements from a Python file."""
    imports = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Find import statements
        import_patterns = [
            r'from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import',
            r'import\s+([a-zA-Z_][a-zA-Z0-9_.]*)',
        ]
        
        for pattern in import_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                # Clean up the import name
                import_name = match.split('.')[0]  # Get the first part
                imports.add(import_name)
                
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return imports

def analyze_file_usage(directory: str) -> Dict[str, Set[str]]:
    """Analyze which files are imported by other files."""
    python_files = get_all_python_files(directory)
    file_usage = {}
    
    for file_path in python_files:
        module_name = os.path.splitext(os.path.basename(file_path))[0]
        imports = extract_imports(file_path)
        file_usage[module_name] = imports
    
    return file_usage

def find_unused_files(directory: str) -> List[str]:
    """Find files that are not imported by any other file."""
    file_usage = analyze_file_usage(directory)
    
    # Get all module names
    all_modules = set(file_usage.keys())
    
    # Get all imported modules
    imported_modules = set()
    for imports in file_usage.values():
        imported_modules.update(imports)
    
    # Files that are imported by others
    used_files = imported_modules.intersection(all_modules)
    
    # Files that are not imported by others
    unused_files = all_modules - used_files
    
    # Convert back to file paths
    unused_file_paths = []
    for module_name in unused_files:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.py') and os.path.splitext(file)[0] == module_name:
                    unused_file_paths.append(os.path.join(root, file))
                    break
    
    return unused_file_paths

def identify_obsolete_files() -> List[str]:
    """Identify files that are likely obsolete based on naming and content."""
    obsolete_patterns = [
        # Test files that are not being used
        r'test_.*\.py$',
        # Backup files
        r'.*\.bak$',
        r'.*\.backup$',
        # Temporary files
        r'.*\.tmp$',
        r'.*\.temp$',
        # Old migration files
        r'migrate_.*\.py$',
        # Duplicate files
        r'.*_copy\.py$',
        r'.*_old\.py$',
    ]
    
    obsolete_files = []
    
    for root, dirs, files in os.walk('.'):
        for file in files:
            file_path = os.path.join(root, file)
            
            # Skip certain directories
            if any(skip_dir in file_path for skip_dir in ['.git', '__pycache__', 'venv', 'node_modules']):
                continue
                
            for pattern in obsolete_patterns:
                if re.match(pattern, file):
                    obsolete_files.append(file_path)
                    break
    
    return obsolete_files

def cleanup_unused_files():
    """Main cleanup function."""
    print("🔍 Analyzing codebase for unused files...")
    
    # Find unused Python files
    unused_files = find_unused_files('.')
    
    # Find obsolete files
    obsolete_files = identify_obsolete_files()
    
    # Combine and remove duplicates
    all_files_to_remove = list(set(unused_files + obsolete_files))
    
    # Filter out files we want to keep
    keep_files = [
        'main.py',
        'config.py',
        'models.py',
        'requirements.txt',
        'Procfile',
        '.gitignore',
        'README.md',
        'plan.md',
        '.cursorrules',
        '.python-version',
    ]
    
    files_to_remove = []
    for file_path in all_files_to_remove:
        filename = os.path.basename(file_path)
        if filename not in keep_files:
            files_to_remove.append(file_path)
    
    print(f"\n📋 Found {len(files_to_remove)} files that can be removed:")
    
    for file_path in files_to_remove:
        print(f"  - {file_path}")
    
    if files_to_remove:
        response = input(f"\n❓ Do you want to remove these {len(files_to_remove)} files? (y/N): ")
        if response.lower() == 'y':
            for file_path in files_to_remove:
                try:
                    os.remove(file_path)
                    print(f"✅ Removed: {file_path}")
                except Exception as e:
                    print(f"❌ Error removing {file_path}: {e}")
        else:
            print("❌ Cleanup cancelled.")
    else:
        print("✅ No unused files found!")

if __name__ == "__main__":
    cleanup_unused_files()
