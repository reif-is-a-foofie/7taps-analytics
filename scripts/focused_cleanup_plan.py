#!/usr/bin/env python3
"""
Focused Cleanup Plan Generator

This script analyzes the project structure and generates a cleanup plan
focused on the main Python project, excluding external frameworks.
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FocusedCleanupPlanGenerator:
    """Generates focused cleanup plans for the main project."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        
        # Directories to ignore (including external frameworks)
        self.ignore_dirs = {
            '.git', '__pycache__', 'node_modules', 'dist', 'build', 
            '.venv', 'venv', '.env', '.pytest_cache', 'chat-ui'
        }
        
        # File patterns to ignore
        self.ignore_patterns = {
            '*.pyc', '*.pyo', '*.pyd', '*.so', '*.dll', '*.exe',
            '.DS_Store', 'Thumbs.db', '*.log', '*.tmp', '*.temp'
        }
        
        # Potential duplicate/temp file patterns
        self.temp_patterns = {
            'temp*', '*temp*', '*copy*', '*copy*', '*final*', '*final2*',
            '*draft*', '*old*', '*backup*', '*bak*', '*~', '*#*#'
        }
    
    def scan_project(self) -> Dict[str, Any]:
        """Scan the project and identify cleanup opportunities."""
        logger.info("🔍 Scanning main project for cleanup opportunities...")
        
        cleanup_plan = {
            'file_renames': [],
            'file_moves': [],
            'file_deletions': [],
            'directory_cleanup': [],
            'documentation_updates': [],
            'structure_issues': []
        }
        
        # Scan all files and directories
        for root, dirs, files in os.walk(self.project_root):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]
            
            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(self.project_root)
                
                # Check for naming issues
                self._check_naming_issues(file_path, relative_path, cleanup_plan)
                
                # Check for temp/duplicate files
                self._check_temp_files(file_path, relative_path, cleanup_plan)
                
                # Check for oversized files
                self._check_oversized_files(file_path, relative_path, cleanup_plan)
        
        # Check directory structure
        self._check_directory_structure(cleanup_plan)
        
        # Check documentation
        self._check_documentation(cleanup_plan)
        
        # Check for redundant files in quarantine
        self._check_quarantine_files(cleanup_plan)
        
        return cleanup_plan
    
    def _check_naming_issues(self, file_path: Path, relative_path: Path, plan: Dict[str, Any]):
        """Check for naming convention violations."""
        filename = file_path.name
        extension = file_path.suffix.lower()
        
        # Python files should be snake_case
        if extension == '.py' and not self._is_snake_case(filename):
            plan['file_renames'].append({
                'current': str(relative_path),
                'suggested': str(relative_path.parent / self._to_snake_case(filename)),
                'reason': 'Python files should use snake_case naming'
            })
    
    def _check_temp_files(self, file_path: Path, relative_path: Path, plan: Dict[str, Any]):
        """Check for temporary or duplicate files."""
        filename = file_path.name.lower()
        
        # Check for temp patterns
        for pattern in self.temp_patterns:
            if pattern.replace('*', '') in filename:
                plan['file_deletions'].append({
                    'file': str(relative_path),
                    'reason': f'Appears to be a temporary file (matches pattern: {pattern})'
                })
                break
        
        # Check for potential duplicates
        if filename.count('copy') > 0 or filename.count('final') > 1:
            plan['file_deletions'].append({
                'file': str(relative_path),
                'reason': 'Appears to be a duplicate or backup file'
            })
    
    def _check_oversized_files(self, file_path: Path, relative_path: Path, plan: Dict[str, Any]):
        """Check for oversized files that might need refactoring."""
        try:
            size_mb = file_path.stat().st_size / (1024 * 1024)
            if size_mb > 1.0:  # Files larger than 1MB
                plan['structure_issues'].append({
                    'file': str(relative_path),
                    'size_mb': round(size_mb, 2),
                    'issue': 'Large file - consider splitting into modules'
                })
        except OSError:
            pass
    
    def _check_directory_structure(self, plan: Dict[str, Any]):
        """Check for directory structure issues."""
        # Check if test files are in the right place
        test_files_outside_tests = []
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]
            
            for file in files:
                if file.startswith('test_') or file.endswith('_test.py'):
                    file_path = Path(root) / file
                    relative_path = file_path.relative_to(self.project_root)
                    
                    if 'tests' not in str(relative_path):
                        test_files_outside_tests.append(str(relative_path))
        
        if test_files_outside_tests:
            plan['file_moves'].extend([
                {
                    'current': test_file,
                    'suggested': f'tests/{Path(test_file).name}',
                    'reason': 'Test files should be in tests/ directory'
                }
                for test_file in test_files_outside_tests
            ])
    
    def _check_documentation(self, plan: Dict[str, Any]):
        """Check for documentation issues."""
        # Check for missing README files in key directories
        key_dirs = ['app', 'scripts', 'tests', 'docs']
        for dir_name in key_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists() and dir_path.is_dir():
                readme_path = dir_path / 'README.md'
                if not readme_path.exists():
                    plan['documentation_updates'].append({
                        'action': 'create',
                        'file': f'{dir_name}/README.md',
                        'reason': f'Missing README.md in {dir_name}/ directory'
                    })
    
    def _check_quarantine_files(self, plan: Dict[str, Any]):
        """Check for files that can be cleaned up from quarantine."""
        quarantine_path = self.project_root / 'quarantine'
        if quarantine_path.exists():
            # Check redundant reports
            redundant_reports = quarantine_path / 'redundant_reports'
            if redundant_reports.exists():
                for file in redundant_reports.glob('*.json'):
                    plan['file_deletions'].append({
                        'file': str(file.relative_to(self.project_root)),
                        'reason': 'Redundant report file in quarantine - no longer needed'
                    })
            
            # Check redundant requirements
            redundant_reqs = quarantine_path / 'redundant_requirements'
            if redundant_reqs.exists():
                for file in redundant_reqs.glob('*.json'):
                    plan['file_deletions'].append({
                        'file': str(file.relative_to(self.project_root)),
                        'reason': 'Redundant requirement file in quarantine - no longer needed'
                    })
    
    def _is_snake_case(self, filename: str) -> bool:
        """Check if filename follows snake_case convention."""
        name_without_ext = filename.rsplit('.', 1)[0]
        return name_without_ext.replace('_', '').replace('-', '').islower()
    
    def _to_snake_case(self, filename: str) -> str:
        """Convert filename to snake_case."""
        name_without_ext = filename.rsplit('.', 1)[0]
        extension = filename.rsplit('.', 1)[1] if '.' in filename else ''
        
        # Convert to snake_case
        import re
        snake_case = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name_without_ext).lower()
        snake_case = re.sub(r'[^a-z0-9_]', '_', snake_case)
        snake_case = re.sub(r'_+', '_', snake_case).strip('_')
        
        return f"{snake_case}.{extension}" if extension else snake_case
    
    def generate_report(self, plan: Dict[str, Any]) -> str:
        """Generate a human-readable cleanup report."""
        report = []
        report.append("# 🧹 Focused Project Cleanup Plan")
        report.append("")
        report.append("*Excluding external frameworks (chat-ui, etc.)*")
        report.append("")
        
        total_actions = sum(len(actions) for actions in plan.values())
        report.append(f"## Summary")
        report.append(f"- **Total actions needed:** {total_actions}")
        report.append(f"- **File renames:** {len(plan['file_renames'])}")
        report.append(f"- **File moves:** {len(plan['file_moves'])}")
        report.append(f"- **File deletions:** {len(plan['file_deletions'])}")
        report.append(f"- **Documentation updates:** {len(plan['documentation_updates'])}")
        report.append(f"- **Structure issues:** {len(plan['structure_issues'])}")
        report.append("")
        
        if plan['file_renames']:
            report.append("## 📝 File Renames")
            for rename in plan['file_renames']:
                report.append(f"- `{rename['current']}` → `{rename['suggested']}`")
                report.append(f"  - **Reason:** {rename['reason']}")
            report.append("")
        
        if plan['file_moves']:
            report.append("## 📁 File Moves")
            for move in plan['file_moves']:
                report.append(f"- `{move['current']}` → `{move['suggested']}`")
                report.append(f"  - **Reason:** {move['reason']}")
            report.append("")
        
        if plan['file_deletions']:
            report.append("## 🗑️ File Deletions")
            for deletion in plan['file_deletions']:
                report.append(f"- `{deletion['file']}`")
                report.append(f"  - **Reason:** {deletion['reason']}")
            report.append("")
        
        if plan['documentation_updates']:
            report.append("## 📚 Documentation Updates")
            for doc in plan['documentation_updates']:
                report.append(f"- **{doc['action'].title()}:** `{doc['file']}`")
                report.append(f"  - **Reason:** {doc['reason']}")
            report.append("")
        
        if plan['structure_issues']:
            report.append("## ⚠️ Structure Issues")
            for issue in plan['structure_issues']:
                report.append(f"- `{issue['file']}` ({issue['size_mb']}MB)")
                report.append(f"  - **Issue:** {issue['issue']}")
            report.append("")
        
        return "\n".join(report)

def main():
    """Main function to generate focused cleanup plan."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate focused project cleanup plan')
    parser.add_argument('--project-root', default='.', help='Project root directory')
    parser.add_argument('--output', help='Output file for the plan')
    
    args = parser.parse_args()
    
    try:
        generator = FocusedCleanupPlanGenerator(args.project_root)
        plan = generator.scan_project()
        report = generator.generate_report(plan)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(report)
            logger.info(f"Focused cleanup plan written to {args.output}")
        else:
            print(report)
        
        # Return exit code based on whether cleanup is needed
        total_actions = sum(len(actions) for actions in plan.values())
        if total_actions > 0:
            logger.info(f"Found {total_actions} focused cleanup actions needed")
            return 1  # Indicate cleanup is needed
        else:
            logger.info("No focused cleanup actions needed - project is clean!")
            return 0
            
    except Exception as e:
        logger.error(f"Error generating focused cleanup plan: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())



