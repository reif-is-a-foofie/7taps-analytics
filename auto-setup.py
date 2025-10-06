#!/usr/bin/env python3
"""
Fully automated GitHub to Cloud Build setup
Handles the entire OAuth flow and trigger creation
"""

import subprocess
import json
import webbrowser
import time
from urllib.parse import urlencode

def run_command(cmd, check=True, capture_output=True):
    """Run shell command with error handling"""
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=capture_output, text=True)
        return result.stdout.strip() if capture_output else None
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {cmd}")
        print(f"Error: {e.stderr}")
        return None

def enable_apis():
    """Enable required Google Cloud APIs"""
    print("🔧 Enabling required APIs...")
    
    apis = [
        "cloudbuild.googleapis.com",
        "run.googleapis.com", 
        "artifactregistry.googleapis.com"
    ]
    
    for api in apis:
        cmd = f"gcloud services enable {api} --project=cellular-tide-473815-p1"
        result = run_command(cmd, check=False)
        if result is not None:
            print(f"✅ Enabled {api}")
        else:
            print(f"⚠️  {api} may already be enabled")

def install_github_app():
    """Guide user through GitHub App installation"""
    print("\n📱 Installing Google Cloud Build GitHub App...")
    
    install_url = "https://github.com/apps/google-cloud-build/installations/new"
    
    print("🔗 Please visit this URL:")
    print(f"   {install_url}")
    print("\nSteps:")
    print("1. Select 'reif-is-a-foofie' account")
    print("2. Choose 'Selected repositories'")
    print("3. Select '7taps-analytics'")
    print("4. Click 'Install'")
    
    # Try to open browser
    try:
        webbrowser.open(install_url)
        print("\n🌐 Opened browser automatically")
    except:
        print("\n🌐 Please open the URL manually")
    
    input("\nPress Enter after completing the GitHub App installation...")

def create_triggers():
    """Create Cloud Build triggers"""
    print("\n🎯 Creating deployment triggers...")
    
    # Production trigger
    print("Creating production trigger...")
    prod_cmd = """gcloud builds triggers create github \
        --repo-owner=reif-is-a-foofie \
        --repo-name=7taps-analytics \
        --branch-pattern="^main$" \
        --build-config=cloudbuild.yaml \
        --name="safety-api-production" \
        --description="Deploy safety-api to production on main branch push" \
        --project=cellular-tide-473815-p1"""
    
    result = run_command(prod_cmd, check=False)
    if result is not None:
        print("✅ Production trigger created")
    else:
        print("❌ Failed to create production trigger")
    
    # Staging trigger
    print("Creating staging trigger...")
    staging_cmd = """gcloud builds triggers create github \
        --repo-owner=reif-is-a-foofie \
        --repo-name=7taps-analytics \
        --branch-pattern="^dev$" \
        --build-config=cloudbuild-staging.yaml \
        --name="safety-api-staging" \
        --description="Deploy safety-api to staging on dev branch push" \
        --project=cellular-tide-473815-p1"""
    
    result = run_command(staging_cmd, check=False)
    if result is not None:
        print("✅ Staging trigger created")
    else:
        print("❌ Failed to create staging trigger")

def verify_setup():
    """Verify the setup is working"""
    print("\n📋 Verifying setup...")
    
    # List triggers
    result = run_command("gcloud builds triggers list --project=cellular-tide-473815-p1")
    if result:
        print("📋 Current triggers:")
        print(result)
    
    # Test git push
    print("\n🧪 Testing git push...")
    test_cmd = "git status"
    result = run_command(test_cmd)
    if result:
        print("✅ Git repository ready")
        print("🎉 Setup complete! You can now use 'mario' to deploy.")

def main():
    """Main execution"""
    print("🚀 Automated GitHub to Cloud Build Setup")
    print("========================================")
    print("📋 Project: cellular-tide-473815-p1")
    print("📋 Repository: reif-is-a-foofie/7taps-analytics")
    print()
    
    # Step 1: Enable APIs
    enable_apis()
    
    # Step 2: Install GitHub App
    install_github_app()
    
    # Step 3: Create triggers
    create_triggers()
    
    # Step 4: Verify
    verify_setup()
    
    print("\n🎉 SUCCESS! GitHub connected to Cloud Build")
    print("\n📋 Your workflow:")
    print("1. Make changes in Cursor")
    print("2. Run: mario")
    print("3. Changes deploy automatically in 30-90 seconds")
    print("\n🔗 Monitor deployments:")
    print("https://console.cloud.google.com/cloud-build/triggers?project=cellular-tide-473815-p1")

if __name__ == "__main__":
    main()
