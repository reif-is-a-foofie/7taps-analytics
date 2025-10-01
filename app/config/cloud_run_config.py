"""
Cloud Run Deployment Configuration for 7taps Analytics UI
Optimized for cost and performance with Google Cloud Run.
"""

import os
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from app.config import settings

class CloudRunConfig(BaseModel):
    """Cloud Run deployment configuration."""
    
    # Service configuration
    service_name: str = Field(default="taps-analytics-ui", description="Cloud Run service name")
    region: str = Field(default=settings.GCP_LOCATION, description="Deployment region")
    project_id: str = Field(default_factory=lambda: settings.GCP_PROJECT_ID, description="GCP project ID")
    
    # Resource allocation
    cpu: str = Field(default="1", description="CPU allocation (1, 2, 4, 6, 8)")
    memory: str = Field(default="2Gi", description="Memory allocation")
    min_instances: int = Field(default=0, description="Minimum number of instances")
    max_instances: int = Field(default=10, description="Maximum number of instances")
    concurrency: int = Field(default=80, description="Concurrent requests per instance")
    
    # Cost optimization settings
    cpu_throttling: bool = Field(default=True, description="Enable CPU throttling when idle")
    request_timeout: int = Field(default=300, description="Request timeout in seconds")
    execution_timeout: int = Field(default=3600, description="Execution timeout in seconds")
    
    # Environment variables
    environment_vars: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    
    # Health check configuration
    health_check_path: str = Field(default="/api/health", description="Health check endpoint")
    health_check_interval: int = Field(default=30, description="Health check interval in seconds")
    health_check_timeout: int = Field(default=5, description="Health check timeout in seconds")
    
    # Security settings
    allow_unauthenticated: bool = Field(default=True, description="Allow unauthenticated access")
    service_account: Optional[str] = Field(default=None, description="Service account email")
    
    # BigQuery optimization
    bigquery_cache_ttl: int = Field(default=3600, description="BigQuery cache TTL in seconds")
    bigquery_cost_threshold: int = Field(default=1048576, description="BigQuery cost threshold in bytes")
    
    def __init__(self, **data):
        super().__init__(**data)
        self._set_default_environment_vars()
    
    def _set_default_environment_vars(self):
        """Set default environment variables for Cloud Run deployment."""
        default_vars = {
            "PORT": os.getenv("PORT", "8080"),
            "ENVIRONMENT": settings.ENVIRONMENT,
            "LOG_LEVEL": settings.LOG_LEVEL.upper(),
            "BIGQUERY_CACHE_TTL": str(self.bigquery_cache_ttl),
            "BIGQUERY_COST_THRESHOLD": str(self.bigquery_cost_threshold),
            "REDIS_URL": os.getenv("REDIS_URL", "redis://localhost:6379"),
            "GCP_PROJECT_ID": settings.GCP_PROJECT_ID,
            "GCP_BIGQUERY_DATASET": settings.GCP_BIGQUERY_DATASET,
            "GCP_LOCATION": settings.GCP_LOCATION,
            "GOOGLE_CLOUD_PROJECT": settings.GCP_PROJECT_ID,
            "DEPLOYMENT_MODE": settings.DEPLOYMENT_MODE,
        }
        if settings.GCP_SERVICE_ACCOUNT_KEY_PATH:
            default_vars["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GCP_SERVICE_ACCOUNT_KEY_PATH
        
        # Merge with provided environment variables
        self.environment_vars = {**default_vars, **self.environment_vars}
    
    def get_deployment_config(self) -> Dict[str, Any]:
        """Get Cloud Run deployment configuration (Cloud Run compliant)."""
        return {
            "apiVersion": "serving.knative.dev/v1",
            "kind": "Service",
            "metadata": {
                "name": self.service_name,
                "namespace": self.project_id,
                "annotations": {
                    "run.googleapis.com/ingress": "all",
                    "run.googleapis.com/execution-environment": "gen2",
                    "autoscaling.knative.dev/minScale": str(self.min_instances),
                    "autoscaling.knative.dev/maxScale": str(self.max_instances),
                    "run.googleapis.com/cpu-throttling": str(self.cpu_throttling).lower()
                }
            },
            "spec": {
                "template": {
                    "spec": {
                        "containerConcurrency": self.concurrency,
                        "timeoutSeconds": self.request_timeout,
                        "containers": [
                            {
                                "image": f"gcr.io/{self.project_id}/{self.service_name}:latest",
                                "ports": [{"containerPort": 8080}],
                                "env": [
                                    {"name": key, "value": value}
                                    for key, value in self.environment_vars.items()
                                ],
                                "resources": {
                                    "limits": {"cpu": self.cpu, "memory": self.memory}
                                }
                            }
                        ]
                    }
                }
            }
        }
    
    def get_gcloud_deploy_command(self) -> str:
        """Get gcloud command for deploying to Cloud Run."""
        env_vars = " ".join([f"--set-env-vars {key}={value}" for key, value in self.environment_vars.items()])

        # Use image deploy and port 8080 for Cloud Run alignment
        return f"""gcloud run deploy {self.service_name} \\
    --image gcr.io/{self.project_id}/{self.service_name}:latest \\
    --platform managed \\
    --region {self.region} \\
    --allow-unauthenticated \\
    --cpu {self.cpu} \\
    --memory {self.memory} \\
    --min-instances {self.min_instances} \\
    --max-instances {self.max_instances} \\
    --concurrency {self.concurrency} \\
    --timeout {self.request_timeout} \\
    --port 8080 \\
    {env_vars}"""

def get_cloud_run_config() -> CloudRunConfig:
    """Get Cloud Run configuration instance."""
    return CloudRunConfig()

def get_cost_optimized_config() -> CloudRunConfig:
    """Get cost-optimized Cloud Run configuration."""
    return CloudRunConfig(
        cpu="0.5",
        memory="1Gi",
        min_instances=0,
        max_instances=5,
        concurrency=100,
        cpu_throttling=True,
        bigquery_cache_ttl=7200,  # 2 hours
        bigquery_cost_threshold=2097152  # 2MB
    )

def get_performance_optimized_config() -> CloudRunConfig:
    """Get performance-optimized Cloud Run configuration."""
    return CloudRunConfig(
        cpu="2",
        memory="4Gi",
        min_instances=1,
        max_instances=20,
        concurrency=50,
        cpu_throttling=False,
        bigquery_cache_ttl=1800,  # 30 minutes
        bigquery_cost_threshold=524288  # 512KB
    )
