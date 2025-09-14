#!/usr/bin/env python3
"""
Setup environment variables for Cloud Run deployment.
This script helps set up the required environment variables for testing.
"""

import os
import sys

def setup_env_vars():
    """Set up environment variables for Cloud Run deployment."""
    
    print("🔧 Setting up environment variables for Cloud Run deployment...")
    
    # Required environment variables
    required_vars = {
        "OPENAI_API_KEY": "Your OpenAI API key (starts with sk-)",
        "DATABASE_URL": "PostgreSQL database URL (postgresql://user:pass@host:port/db)",
        "REDIS_URL": "Redis URL (redis://host:port or leave empty for optional)"
    }
    
    # Check current environment
    print("\n📋 Current environment variables:")
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if "KEY" in var or "URL" in var:
                masked_value = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                print(f"  ✅ {var}: {masked_value}")
            else:
                print(f"  ✅ {var}: {value}")
        else:
            print(f"  ❌ {var}: Not set")
    
    # Interactive setup
    print("\n🔑 Interactive setup (press Enter to skip):")
    for var, description in required_vars.items():
        current_value = os.getenv(var)
        if not current_value:
            print(f"\n{description}")
            value = input(f"Enter {var} (or press Enter to skip): ").strip()
            if value:
                os.environ[var] = value
                print(f"✅ Set {var}")
            else:
                print(f"⏭️  Skipped {var}")
        else:
            print(f"⏭️  {var} already set")
    
    # Export for current session
    print("\n📝 To export these variables for your current shell session:")
    for var in required_vars.keys():
        value = os.getenv(var)
        if value:
            print(f"export {var}='{value}'")
    
    # Check if all required vars are set
    missing_vars = [var for var in required_vars.keys() if not os.getenv(var)]
    
    if missing_vars:
        print(f"\n⚠️  Warning: Missing required environment variables: {', '.join(missing_vars)}")
        print("The app may not function properly without these variables.")
        return False
    else:
        print("\n✅ All required environment variables are set!")
        return True

def main():
    """Main function."""
    success = setup_env_vars()
    
    if success:
        print("\n🚀 Ready to deploy! Run: python3 scripts/deploy_cloud_run_ui.py")
    else:
        print("\n❌ Please set the missing environment variables and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()

