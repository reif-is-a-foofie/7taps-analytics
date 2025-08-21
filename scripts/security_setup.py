#!/usr/bin/env python3
"""
Security Setup Script for 7taps Analytics

This script helps validate environment variables and provides guidance
for proper security configuration.
"""

import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Any

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")

def check_env_file():
    """Check if .env file exists and is properly configured"""
    env_file = Path('.env')
    
    if not env_file.exists():
        print("❌ .env file not found!")
        print("📝 Create a .env file with the following structure:")
        print()
        print("# Required: Database Configuration")
        print("DATABASE_URL=postgresql://username:password@localhost:5432/database_name")
        print("PGSSLMODE=require")
        print()
        print("# Required: OpenAI API Configuration")
        print("OPENAI_API_KEY=sk-proj-your-openai-api-key-here")
        print()
        print("# Optional: Redis Configuration")
        print("REDIS_URL=redis://localhost:6379/0")
        print()
        return False
    
    print("✅ .env file found")
    return True

def validate_api_key_format(api_key: str) -> bool:
    """Validate OpenAI API key format"""
    if not api_key:
        return False
    
    # OpenAI API keys start with 'sk-' and are typically 51 characters
    if not api_key.startswith('sk-'):
        return False
    
    if len(api_key) < 20:
        return False
    
    return True

def check_gitignore():
    """Check if .env files are properly ignored"""
    gitignore_file = Path('.gitignore')
    
    if not gitignore_file.exists():
        print("❌ .gitignore file not found!")
        return False
    
    with open(gitignore_file, 'r') as f:
        content = f.read()
    
    if '.env' in content:
        print("✅ .env files are properly ignored in .gitignore")
        return True
    else:
        print("❌ .env files are not ignored in .gitignore!")
        print("📝 Add '.env' to your .gitignore file")
        return False

def validate_environment_variables() -> Dict[str, Any]:
    """Validate all required environment variables"""
    results = {
        'valid': True,
        'missing': [],
        'weak': [],
        'valid_vars': []
    }
    
    required_vars = {
        'DATABASE_URL': {
            'min_length': 10,
            'description': 'PostgreSQL connection string'
        },
        'OPENAI_API_KEY': {
            'min_length': 20,
            'description': 'OpenAI API key for NLP features'
        }
    }
    
    optional_vars = {
        'REDIS_URL': {
            'min_length': 10,
            'description': 'Redis connection string for background jobs'
        },
        'APP_PORT': {
            'min_length': 1,
            'description': 'Application port number'
        }
    }
    
    print("\n🔍 Validating environment variables...")
    
    # Check required variables
    for var_name, config in required_vars.items():
        value = os.getenv(var_name)
        
        if not value:
            results['missing'].append(var_name)
            results['valid'] = False
            print(f"❌ Missing required variable: {var_name}")
        elif len(value) < config['min_length']:
            results['weak'].append(var_name)
            print(f"⚠️  Weak variable: {var_name} (too short)")
        else:
            results['valid_vars'].append(var_name)
            print(f"✅ Valid variable: {var_name}")
    
    # Check optional variables
    for var_name, config in optional_vars.items():
        value = os.getenv(var_name)
        
        if value:
            if len(value) < config['min_length']:
                results['weak'].append(var_name)
                print(f"⚠️  Weak optional variable: {var_name} (too short)")
            else:
                results['valid_vars'].append(var_name)
                print(f"✅ Valid optional variable: {var_name}")
        else:
            print(f"ℹ️  Optional variable not set: {var_name}")
    
    # Special validation for OpenAI API key
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key:
        if not validate_api_key_format(openai_key):
            results['weak'].append('OPENAI_API_KEY')
            print("⚠️  OpenAI API key format appears invalid")
        else:
            print("✅ OpenAI API key format is valid")
    
    return results

def check_git_history():
    """Check git history for potential secrets"""
    print("\n🔍 Checking git history for secrets...")
    
    try:
        import subprocess
        
        # Check for API keys in git log
        result = subprocess.run(
            ['git', 'log', '--all', '--full-history', '--', '.'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            # Look for potential API keys
            api_key_pattern = r'sk-[a-zA-Z0-9]{20,}'
            matches = re.findall(api_key_pattern, result.stdout)
            
            if matches:
                print(f"⚠️  Found {len(matches)} potential API keys in git history")
                print("   Consider using BFG Repo-Cleaner or git filter-branch to remove them")
                return False
            else:
                print("✅ No API keys found in git history")
                return True
        else:
            print("ℹ️  Could not check git history (not a git repository or other issue)")
            return True
            
    except Exception as e:
        print(f"ℹ️  Could not check git history: {e}")
        return True

def provide_recommendations(results: Dict[str, Any]):
    """Provide security recommendations based on validation results"""
    print("\n📋 Security Recommendations:")
    
    if results['missing']:
        print("\n🔴 Critical Issues:")
        for var in results['missing']:
            print(f"   - Set the {var} environment variable")
    
    if results['weak']:
        print("\n🟡 Security Warnings:")
        for var in results['weak']:
            print(f"   - Review and strengthen the {var} value")
    
    print("\n🟢 Best Practices:")
    print("   - Rotate API keys every 90 days")
    print("   - Use different keys for development/staging/production")
    print("   - Monitor API key usage for suspicious activity")
    print("   - Use HTTPS in production environments")
    print("   - Implement proper access controls")
    print("   - Regular security audits")
    
    print("\n🔧 Next Steps:")
    print("   1. Set up your .env file with proper values")
    print("   2. Test the application with: python -m app.main")
    print("   3. Check security status at: http://localhost:8000/api/security/status")
    print("   4. Review the security documentation in docs/SECURITY.md")

def main():
    """Main security setup validation"""
    print("🔐 7taps Analytics Security Setup Validation")
    print("=" * 50)
    
    # Check .env file
    env_exists = check_env_file()
    
    # Check .gitignore
    gitignore_valid = check_gitignore()
    
    # Validate environment variables
    env_results = validate_environment_variables()
    
    # Check git history
    git_history_clean = check_git_history()
    
    # Provide recommendations
    provide_recommendations(env_results)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Security Setup Summary:")
    print(f"   .env file: {'✅' if env_exists else '❌'}")
    print(f"   .gitignore: {'✅' if gitignore_valid else '❌'}")
    print(f"   Environment variables: {'✅' if env_results['valid'] else '❌'}")
    print(f"   Git history: {'✅' if git_history_clean else '⚠️'}")
    
    if env_results['valid'] and env_exists and gitignore_valid:
        print("\n🎉 Security setup looks good!")
        print("   You can now run the application safely.")
    else:
        print("\n⚠️  Please address the issues above before proceeding.")
        sys.exit(1)

if __name__ == "__main__":
    main()
