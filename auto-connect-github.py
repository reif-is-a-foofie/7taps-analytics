#!/usr/bin/env python3
"""
Automatically connect GitHub to Cloud Build and create deployment triggers
This script handles the OAuth flow and trigger creation programmatically
"""

import subprocess
import json
import time
import webbrowser
from urllib.parse import urlencode
import requests
import os

class GitHubCloudBuildConnector:
    def __init__(self, project_id="cellular-tide-473815-p1"):
        self.project_id = project_id
        self.repo_owner = "reif-is-a-foofie"
        self.repo_name = "7taps-analytics"
        
    def enable_apis(self):
        """Enable required Google Cloud APIs"""
        print("🔧 Enabling required APIs...")
        
        apis = [
            "cloudbuild.googleapis.com",
            "run.googleapis.com", 
            "artifactregistry.googleapis.com"
        ]
        
        for api in apis:
            try:
                subprocess.run([
                    "gcloud", "services", "enable", api, 
                    f"--project={self.project_id}"
                ], check=True, capture_output=True)
                print(f"✅ Enabled {api}")
            except subprocess.CalledProcessError as e:
                print(f"⚠️  API {api} may already be enabled")
                
    def get_github_token(self):
        """Get GitHub token for API access"""
        print("🔑 Getting GitHub token...")
        
        # Check if token exists in environment
        token = os.getenv("GITHUB_TOKEN")
        if token:
            print("✅ Using existing GITHUB_TOKEN")
            return token
            
        # Check if token exists in gh CLI
        try:
            result = subprocess.run([
                "gh", "auth", "token"
            ], capture_output=True, text=True, check=True)
            token = result.stdout.strip()
            print("✅ Using GitHub CLI token")
            return token
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ No GitHub token found")
            print("Please set GITHUB_TOKEN environment variable or run: gh auth login")
            return None
            
    def install_github_app(self):
        """Install Google Cloud Build GitHub App"""
        print("📱 Installing Google Cloud Build GitHub App...")
        
        # GitHub App installation URL
        app_id = "964578067"  # Google Cloud Build GitHub App ID
        install_url = f"https://github.com/apps/google-cloud-build/installations/new"
        
        print(f"🔗 Please visit: {install_url}")
        print("1. Select 'reif-is-a-foofie' account")
        print("2. Choose 'Selected repositories'")
        print("3. Select '7taps-analytics'")
        print("4. Click 'Install'")
        
        # Try to open browser automatically
        try:
            webbrowser.open(install_url)
            print("🌐 Opened browser automatically")
        except:
            print("🌐 Please open the URL manually")
            
        input("Press Enter after completing the GitHub App installation...")
        
    def create_trigger_via_api(self, trigger_config):
        """Create Cloud Build trigger using REST API"""
        print(f"🎯 Creating trigger: {trigger_config['name']}")
        
        url = f"https://cloudbuild.googleapis.com/v1/projects/{self.project_id}/triggers"
        
        headers = {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(url, headers=headers, json=trigger_config)
            response.raise_for_status()
            print(f"✅ Created trigger: {trigger_config['name']}")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to create trigger: {e}")
            return None
            
    def _get_access_token(self):
        """Get Google Cloud access token"""
        try:
            result = subprocess.run([
                "gcloud", "auth", "print-access-token"
            ], capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            print("❌ Failed to get access token. Please run: gcloud auth login")
            return None
            
    def create_production_trigger(self):
        """Create production deployment trigger"""
        trigger_config = {
            "name": "safety-api-production",
            "description": "Deploy safety-api to production on main branch push",
            "github": {
                "owner": self.repo_owner,
                "name": self.repo_name,
                "push": {
                    "branch": "^main$"
                }
            },
            "filename": "cloudbuild.yaml",
            "substitutions": {
                "_GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", "your-actual-gemini-api-key")
            }
        }
        
        return self.create_trigger_via_api(trigger_config)
        
    def create_staging_trigger(self):
        """Create staging deployment trigger"""
        trigger_config = {
            "name": "safety-api-staging", 
            "description": "Deploy safety-api to staging on dev branch push",
            "github": {
                "owner": self.repo_owner,
                "name": self.repo_name,
                "push": {
                    "branch": "^dev$"
                }
            },
            "filename": "cloudbuild-staging.yaml",
            "substitutions": {
                "_GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", "your-actual-gemini-api-key")
            }
        }
        
        return self.create_trigger_via_api(trigger_config)
        
    def test_triggers(self):
        """Test the created triggers"""
        print("🧪 Testing triggers...")
        
        try:
            result = subprocess.run([
                "gcloud", "builds", "triggers", "list",
                f"--project={self.project_id}"
            ], capture_output=True, text=True, check=True)
            
            print("📋 Current triggers:")
            print(result.stdout)
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to list triggers: {e}")
            
    def run(self):
        """Main execution flow"""
        print("🚀 GitHub to Cloud Build Auto-Connector")
        print(f"📋 Project: {self.project_id}")
        print(f"📋 Repository: {self.repo_owner}/{self.repo_name}")
        print()
        
        # Step 1: Enable APIs
        self.enable_apis()
        print()
        
        # Step 2: Install GitHub App
        self.install_github_app()
        print()
        
        # Step 3: Create triggers
        print("🎯 Creating deployment triggers...")
        prod_result = self.create_production_trigger()
        staging_result = self.create_staging_trigger()
        print()
        
        # Step 4: Test
        self.test_triggers()
        print()
        
        # Step 5: Success message
        if prod_result and staging_result:
            print("🎉 SUCCESS! GitHub connected to Cloud Build")
            print()
            print("📋 Your workflow:")
            print("1. Make changes in Cursor")
            print("2. Run: mario")
            print("3. Changes deploy automatically in 30-90 seconds")
            print()
            print("🔗 Monitor deployments:")
            print(f"https://console.cloud.google.com/cloud-build/triggers?project={self.project_id}")
        else:
            print("❌ Some triggers failed to create. Check the errors above.")

if __name__ == "__main__":
    connector = GitHubCloudBuildConnector()
    connector.run()
