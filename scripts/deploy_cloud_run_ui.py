#!/usr/bin/env python3
"""
Deploy 7taps Analytics UI to Google Cloud Run
This script chains raw gcloud commands and runs comprehensive testing.
"""

import os
import subprocess
import json
import logging
import sys
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CloudRunDeployment:
    """Deploy FastAPI UI to Google Cloud Run with raw command chaining."""
    
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT", os.getenv("GCP_PROJECT_ID", "taps-data"))
        self.region = os.getenv("GCP_REGION", "us-central1")
        self.service_name = os.getenv("CLOUD_RUN_SERVICE_NAME", "taps-analytics-ui")
        # Allow overriding image (e.g., Artifact Registry) via env
        self.image_name = os.getenv("CLOUD_RUN_IMAGE", f"gcr.io/{self.project_id}/{self.service_name}")
        # Optional dedicated service account
        self.service_account = os.getenv("CLOUD_RUN_SERVICE_ACCOUNT")
        
    def run_command(self, cmd: list, description: str) -> bool:
        """Run a command and log the output."""
        logger.info(f"🔧 {description}")
        logger.info(f"Command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.stdout:
                logger.info(f"STDOUT: {result.stdout}")
            if result.stderr:
                logger.warning(f"STDERR: {result.stderr}")
                
            if result.returncode == 0:
                logger.info(f"✅ {description} - SUCCESS")
                return True
            else:
                logger.error(f"❌ {description} - FAILED (exit code: {result.returncode})")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"❌ {description} - TIMEOUT")
            return False
        except Exception as e:
            logger.error(f"❌ {description} - ERROR: {e}")
            return False
    
    def setup_permissions(self) -> bool:
        """Set up necessary IAM permissions for the Cloud Run service."""
        logger.info("🔐 Setting up IAM permissions...")
        
        service_account = self.service_account
        if not service_account:
            logger.info("No CLOUD_RUN_SERVICE_ACCOUNT provided; using current service identity bindings where applicable.")
        else:
            logger.info(f"Using service account: {service_account}")
        
        # Grant BigQuery permissions
        permissions = [
            ("roles/bigquery.dataViewer", "BigQuery Data Viewer"),
            ("roles/bigquery.jobUser", "BigQuery Job User"),
            ("roles/pubsub.publisher", "Pub/Sub Publisher")
        ]
        
        for role, description in permissions:
            if service_account:
                cmd = [
                    "gcloud", "projects", "add-iam-policy-binding", self.project_id,
                    "--member", f"serviceAccount:{service_account}",
                    "--role", role
                ]
                if not self.run_command(cmd, f"Grant {description}"):
                    logger.warning(f"Failed to grant {description} - continuing...")
        
        return True
    
    def build_and_push_image(self) -> bool:
        """Build and push Docker image using raw gcloud command."""
        cmd = [
            "gcloud", "builds", "submit",
            "--tag", self.image_name,
            "--project", self.project_id,
            "."
        ]
        
        return self.run_command(cmd, "Build and push Docker image")
    
    def deploy_to_cloud_run(self) -> bool:
        """Deploy to Cloud Run using raw gcloud command."""
        cmd = [
            "gcloud", "run", "deploy", self.service_name,
            "--image", self.image_name,
            "--platform", "managed",
            "--region", self.region,
            "--project", self.project_id,
            "--allow-unauthenticated",
            "--port", "8080",
            "--memory", "2Gi",
            "--cpu", "1",
            "--min-instances", "0",
            "--max-instances", "10",
            "--concurrency", "80",
            "--timeout", "300",
            "--set-env-vars", "API_BASE_URL=",
            "--set-env-vars", "DATABASE_TERMINAL_URL=https://your-sqlpad-instance.run.app",
            "--set-env-vars", f"GOOGLE_CLOUD_PROJECT={self.project_id}",
            "--set-env-vars", f"GCP_REGION={self.region}",
            "--set-env-vars", "ENVIRONMENT=production",
            "--set-env-vars", "PUBSUB_TOPIC=xapi-ingestion-topic",
            "--set-env-vars", "STORAGE_BUCKET=taps-data-raw-xapi"
        ]

        if self.service_account:
            cmd.extend(["--service-account", self.service_account])

        return self.run_command(cmd, "Deploy to Cloud Run")
    
    def get_service_url(self) -> str:
        """Get the deployed service URL."""
        cmd = [
            "gcloud", "run", "services", "describe", self.service_name,
            "--platform", "managed",
            "--region", self.region,
            "--project", self.project_id,
            "--format", "value(status.url)"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            logger.error(f"Failed to get service URL: {result.stderr}")
            return ""
    
    def run_comprehensive_tests(self, service_url: str) -> Dict[str, Any]:
        """Run the comprehensive test suite."""
        logger.info("🧪 Running comprehensive test suite...")
        
        # Change to project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.chdir(project_root)
        
        # Run the comprehensive test suite
        cmd = ["python3", "comprehensive_test_suite.py"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            logger.info("Test Suite Output:")
            logger.info(result.stdout)
            
            if result.stderr:
                logger.warning(f"Test Suite Errors: {result.stderr}")
            
            # Parse test results from output
            test_results = {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            }
            
            # Try to extract pass rate from output
            if "Pass Rate:" in result.stdout:
                for line in result.stdout.split('\n'):
                    if "Pass Rate:" in line:
                        try:
                            pass_rate = float(line.split("Pass Rate:")[1].split("%")[0].strip())
                            test_results["pass_rate"] = pass_rate
                        except:
                            pass
                        break
            
            return test_results
            
        except subprocess.TimeoutExpired:
            logger.error("Test suite timed out")
            return {"success": False, "error": "Test suite timed out"}
        except Exception as e:
            logger.error(f"Error running test suite: {e}")
            return {"success": False, "error": str(e)}
    
    def run_xapi_pipeline_test(self, service_url: str) -> Dict[str, Any]:
        """Run the xAPI pipeline test."""
        logger.info("📡 Running xAPI pipeline test...")
        
        # Change to project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.chdir(project_root)
        
        # Set up environment for xAPI test
        env = os.environ.copy()
        env["GOOGLE_APPLICATION_CREDENTIALS"] = "google-cloud-key.json"
        
        # Run the xAPI pipeline test
        cmd = ["python3", "test_pubsub_xapi.py"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
            
            logger.info("xAPI Pipeline Test Output:")
            logger.info(result.stdout)
            
            if result.stderr:
                logger.warning(f"xAPI Pipeline Test Errors: {result.stderr}")
            
            return {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            }
            
        except subprocess.TimeoutExpired:
            logger.error("xAPI pipeline test timed out")
            return {"success": False, "error": "xAPI pipeline test timed out"}
        except Exception as e:
            logger.error(f"Error running xAPI pipeline test: {e}")
            return {"success": False, "error": str(e)}
    
    def deploy(self) -> Dict[str, Any]:
        """Complete deployment process with testing."""
        logger.info("🚀 Starting Cloud Run UI deployment with testing...")
        
        results = {
            "deployment": {"success": False},
            "permissions": {"success": False},
            "testing": {"success": False},
            "xapi_pipeline": {"success": False}
        }
        
        # Step 1: Build and push image
        logger.info("=" * 60)
        logger.info("STEP 1: BUILD AND PUSH DOCKER IMAGE")
        logger.info("=" * 60)
        
        if not self.build_and_push_image():
            results["deployment"]["error"] = "Failed to build Docker image"
            return results
        
        # Step 2: Set up permissions
        logger.info("=" * 60)
        logger.info("STEP 2: SET UP IAM PERMISSIONS")
        logger.info("=" * 60)
        
        self.setup_permissions()
        results["permissions"]["success"] = True
        
        # Step 3: Deploy to Cloud Run
        logger.info("=" * 60)
        logger.info("STEP 3: DEPLOY TO CLOUD RUN")
        logger.info("=" * 60)
        
        if not self.deploy_to_cloud_run():
            results["deployment"]["error"] = "Failed to deploy to Cloud Run"
            return results
        
        results["deployment"]["success"] = True
        
        # Step 4: Get service URL
        service_url = self.get_service_url()
        if not service_url:
            results["deployment"]["error"] = "Could not get service URL"
            return results
        
        results["deployment"]["service_url"] = service_url
        logger.info(f"🌐 Service URL: {service_url}")
        
        # Step 5: Run comprehensive tests
        logger.info("=" * 60)
        logger.info("STEP 4: RUN COMPREHENSIVE TEST SUITE")
        logger.info("=" * 60)
        
        test_results = self.run_comprehensive_tests(service_url)
        results["testing"] = test_results
        
        # Step 6: Run xAPI pipeline test
        logger.info("=" * 60)
        logger.info("STEP 5: RUN XAPI PIPELINE TEST")
        logger.info("=" * 60)
        
        xapi_results = self.run_xapi_pipeline_test(service_url)
        results["xapi_pipeline"] = xapi_results
        
        # Overall success
        overall_success = (
            results["deployment"]["success"] and
            results["permissions"]["success"] and
            results["testing"]["success"]
        )
        
        results["overall_success"] = overall_success
        
        return results

def main():
    """Main deployment function."""
    deployment = CloudRunDeployment()
    result = deployment.deploy()
    
    logger.info("=" * 60)
    logger.info("DEPLOYMENT SUMMARY")
    logger.info("=" * 60)
    
    print(json.dumps(result, indent=2))
    
    if result["overall_success"]:
        logger.info("🎉 DEPLOYMENT SUCCESSFUL!")
        logger.info(f"📊 Service URL: {result['deployment']['service_url']}")
        
        if "pass_rate" in result["testing"]:
            logger.info(f"🧪 Test Pass Rate: {result['testing']['pass_rate']}%")
        
        if result["xapi_pipeline"]["success"]:
            logger.info("📡 xAPI Pipeline: WORKING")
        else:
            logger.info("📡 xAPI Pipeline: NEEDS ATTENTION")
            
    else:
        logger.error("❌ DEPLOYMENT FAILED!")
        if "error" in result["deployment"]:
            logger.error(f"Deployment Error: {result['deployment']['error']}")
        if not result["testing"]["success"]:
            logger.error("Testing Failed - check logs above")
        if not result["xapi_pipeline"]["success"]:
            logger.error("xAPI Pipeline Failed - check logs above")
        
        sys.exit(1)

if __name__ == "__main__":
    main()
