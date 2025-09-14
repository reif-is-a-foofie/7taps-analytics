#!/usr/bin/env python3
"""
Google Cloud Platform Python-Only Deployment Script

This script deploys GCP resources using only Python client libraries,
without requiring the gcloud CLI. It's more efficient and doesn't
require additional system dependencies.

Usage:
    python deploy_gcp_python_only.py [--dry-run]
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from google.cloud import pubsub_v1, storage, bigquery, resourcemanager_v3
    from google.api_core import exceptions as google_exceptions
    from google.auth import default
    from google.oauth2 import service_account
    from googleapiclient import discovery
    from googleapiclient.errors import HttpError
except ImportError as e:
    print(f"❌ Error importing Google Cloud dependencies: {e}")
    print("Please install required packages:")
    print("pip install google-cloud-pubsub google-cloud-storage google-cloud-bigquery")
    print("pip install google-auth google-auth-oauthlib google-auth-httplib2")
    print("pip install google-api-python-client")
    sys.exit(1)

class GCPPythonDeployer:
    """Deploys GCP resources using Python client libraries only."""

    def __init__(self, config_file: str = None, dry_run: bool = False):
        self.dry_run = dry_run
        self.config = self.load_config(config_file)
        self.credentials = self.get_credentials()
        self.project_id = self.config['gcp_project']['name']

        # Initialize clients
        self.pubsub_publisher = pubsub_v1.PublisherClient(credentials=self.credentials)
        self.pubsub_subscriber = pubsub_v1.SubscriberClient(credentials=self.credentials)
        self.storage_client = storage.Client(credentials=self.credentials)
        self.bq_client = bigquery.Client(credentials=self.credentials)
        
        # Initialize service management client for API enablement
        self.service_client = discovery.build('serviceusage', 'v1', credentials=self.credentials)

        self.results = {}
        self.errors = []

    def load_config(self, config_file: str = None) -> Dict[str, Any]:
        """Load GCP deployment configuration."""
        if not config_file:
            config_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'config', 'gcp_deployment_config.json'
            )

        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ Configuration file not found: {config_file}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in configuration file: {e}")
            sys.exit(1)

    def get_credentials(self):
        """Get Google Cloud credentials."""
        key_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'google-cloud-key.json'
        )

        if os.path.exists(key_file):
            return service_account.Credentials.from_service_account_file(key_file)
        else:
            # Try to use default credentials
            credentials, _ = default()
            return credentials

    def enable_gcp_apis(self) -> bool:
        """Enable required Google Cloud APIs using Python client."""
        print("🔌 Enabling Google Cloud APIs...")

        success_count = 0
        for api in self.config['enabled_apis']:
            if self.dry_run:
                print(f"🔍 DRY RUN: Enable {api}")
                success_count += 1
                continue

            try:
                print(f"🔧 Enabling {api}...")
                
                # Use service usage API to enable services
                service_name = f"projects/{self.project_id}/services/{api}"
                
                request = self.service_client.services().enable(name=service_name)
                request.execute()
                
                print(f"   ✅ Enabled {api}")
                success_count += 1
            except HttpError as e:
                if e.resp.status == 409:  # Already enabled
                    print(f"   ⚠️  API already enabled: {api}")
                    success_count += 1
                else:
                    print(f"   ❌ Failed to enable {api}: {e}")
                    self.errors.append(f"Failed to enable {api}: {e}")
            except Exception as e:
                print(f"   ❌ Failed to enable {api}: {e}")
                self.errors.append(f"Failed to enable {api}: {e}")

        self.results['apis_enabled'] = success_count
        return success_count == len(self.config['enabled_apis'])

    def create_pubsub_topics(self) -> bool:
        """Create Pub/Sub topics."""
        print("📡 Creating Pub/Sub topics...")

        success_count = 0
        for topic_config in self.config['pubsub']['topics']:
            topic_path = self.pubsub_publisher.topic_path(self.project_id, topic_config['name'])

            if self.dry_run:
                print(f"🔍 DRY RUN: Create topic {topic_config['name']}")
                success_count += 1
                continue

            try:
                topic = self.pubsub_publisher.create_topic(
                    request={"name": topic_path, "labels": topic_config.get('labels', {})}
                )
                print(f"   ✅ Created topic: {topic.name}")
                success_count += 1
            except google_exceptions.AlreadyExists:
                print(f"   ⚠️  Topic already exists: {topic_config['name']}")
                success_count += 1
            except Exception as e:
                print(f"   ❌ Failed to create topic {topic_config['name']}: {e}")
                self.errors.append(f"Failed to create topic {topic_config['name']}: {e}")

        self.results['pubsub_topics'] = success_count
        return success_count == len(self.config['pubsub']['topics'])

    def create_pubsub_subscriptions(self) -> bool:
        """Create Pub/Sub subscriptions."""
        print("📡 Creating Pub/Sub subscriptions...")

        success_count = 0
        for sub_config in self.config['pubsub']['subscriptions']:
            subscription_path = self.pubsub_subscriber.subscription_path(
                self.project_id, sub_config['name']
            )
            topic_path = self.pubsub_publisher.topic_path(
                self.project_id, sub_config['topic']
            )

            if self.dry_run:
                print(f"🔍 DRY RUN: Create subscription {sub_config['name']}")
                success_count += 1
                continue

            try:
                subscription = self.pubsub_subscriber.create_subscription(
                    request={
                        "name": subscription_path,
                        "topic": topic_path,
                        "ack_deadline_seconds": sub_config.get('ack_deadline_seconds', 60),
                        "labels": sub_config.get('labels', {})
                    }
                )
                print(f"   ✅ Created subscription: {subscription.name}")
                success_count += 1
            except google_exceptions.AlreadyExists:
                print(f"   ⚠️  Subscription already exists: {sub_config['name']}")
                success_count += 1
            except Exception as e:
                print(f"   ❌ Failed to create subscription {sub_config['name']}: {e}")
                self.errors.append(f"Failed to create subscription {sub_config['name']}: {e}")

        self.results['pubsub_subscriptions'] = success_count
        return success_count == len(self.config['pubsub']['subscriptions'])

    def create_storage_buckets(self) -> bool:
        """Create Cloud Storage buckets."""
        print("🪣 Creating Cloud Storage buckets...")

        success_count = 0
        for bucket_config in self.config['cloud_storage']['buckets']:
            if self.dry_run:
                print(f"🔍 DRY RUN: Create bucket {bucket_config['name']}")
                success_count += 1
                continue

            try:
                bucket = self.storage_client.bucket(bucket_config['name'])
                bucket.location = bucket_config.get('location', 'us-central1')
                bucket.storage_class = bucket_config.get('storage_class', 'STANDARD')
                bucket = self.storage_client.create_bucket(bucket)

                # Set labels if provided
                if 'labels' in bucket_config:
                    bucket.labels = bucket_config['labels']
                    bucket.patch()

                print(f"   ✅ Created bucket: {bucket.name}")
                success_count += 1
            except google_exceptions.Conflict:
                print(f"   ⚠️  Bucket already exists: {bucket_config['name']}")
                success_count += 1
            except Exception as e:
                print(f"   ❌ Failed to create bucket {bucket_config['name']}: {e}")
                self.errors.append(f"Failed to create bucket {bucket_config['name']}: {e}")

        self.results['storage_buckets'] = success_count
        return success_count == len(self.config['cloud_storage']['buckets'])

    def create_bigquery_datasets(self) -> bool:
        """Create BigQuery datasets."""
        print("📊 Creating BigQuery datasets...")

        success_count = 0
        for dataset_config in self.config['bigquery']['datasets']:
            dataset_ref = self.bq_client.dataset(dataset_config['dataset_id'])

            if self.dry_run:
                print(f"🔍 DRY RUN: Create dataset {dataset_config['dataset_id']}")
                success_count += 1
                continue

            try:
                dataset = bigquery.Dataset(dataset_ref)
                dataset.friendly_name = dataset_config.get('friendly_name', dataset_config['dataset_id'])
                dataset.description = dataset_config.get('description', '')
                dataset.location = dataset_config.get('location', 'us-central1')

                if 'labels' in dataset_config:
                    dataset.labels = dataset_config['labels']

                dataset = self.bq_client.create_dataset(dataset)
                print(f"   ✅ Created dataset: {dataset.dataset_id}")
                success_count += 1
            except google_exceptions.Conflict:
                print(f"   ⚠️  Dataset already exists: {dataset_config['dataset_id']}")
                success_count += 1
            except Exception as e:
                print(f"   ❌ Failed to create dataset {dataset_config['dataset_id']}: {e}")
                self.errors.append(f"Failed to create dataset {dataset_config['dataset_id']}: {e}")

        self.results['bigquery_datasets'] = success_count
        return success_count == len(self.config['bigquery']['datasets'])

    def create_bigquery_tables(self) -> bool:
        """Create BigQuery tables."""
        print("📋 Creating BigQuery tables...")

        success_count = 0
        for table_config in self.config['bigquery']['tables']:
            table_ref = self.bq_client.dataset(table_config['dataset_id']).table(table_config['table_id'])

            if self.dry_run:
                print(f"🔍 DRY RUN: Create table {table_config['dataset_id']}.{table_config['table_id']}")
                success_count += 1
                continue

            try:
                table = bigquery.Table(table_ref, schema=table_config['schema'])

                if 'description' in table_config:
                    table.description = table_config['description']

                if 'time_partitioning' in table_config:
                    # Fix the parameter name from 'type' to 'type_'
                    partitioning_config = table_config['time_partitioning'].copy()
                    if 'type' in partitioning_config:
                        partitioning_config['type_'] = partitioning_config.pop('type')
                    table.time_partitioning = bigquery.TimePartitioning(**partitioning_config)

                table = self.bq_client.create_table(table)
                print(f"   ✅ Created table: {table.table_id}")
                success_count += 1
            except google_exceptions.Conflict:
                print(f"   ⚠️  Table already exists: {table_config['dataset_id']}.{table_config['table_id']}")
                success_count += 1
            except Exception as e:
                print(f"   ❌ Failed to create table {table_config['dataset_id']}.{table_config['table_id']}: {e}")
                self.errors.append(f"Failed to create table {table_config['dataset_id']}.{table_config['table_id']}: {e}")

        self.results['bigquery_tables'] = success_count
        return success_count == len(self.config['bigquery']['tables'])

    def validate_deployment(self) -> Dict[str, Any]:
        """Validate the complete deployment."""
        print("🔍 Validating deployment...")

        validation_results = {}

        # Validate Pub/Sub
        try:
            topics = list(self.pubsub_publisher.list_topics(request={"project": f"projects/{self.project_id}"}))
            validation_results['pubsub_topics'] = len([t for t in topics if any(topic['name'] in t.name for topic in self.config['pubsub']['topics'])])
        except Exception as e:
            validation_results['pubsub_topics'] = 0
            self.errors.append(f"Pub/Sub validation failed: {e}")

        # Validate Storage
        try:
            buckets = list(self.storage_client.list_buckets())
            validation_results['storage_buckets'] = len([b for b in buckets if b.name in [bucket['name'] for bucket in self.config['cloud_storage']['buckets']]])
        except Exception as e:
            validation_results['storage_buckets'] = 0
            self.errors.append(f"Storage validation failed: {e}")

        # Validate BigQuery
        try:
            datasets = list(self.bq_client.list_datasets())
            validation_results['bigquery_datasets'] = len([d for d in datasets if d.dataset_id in [ds['dataset_id'] for ds in self.config['bigquery']['datasets']]])
        except Exception as e:
            validation_results['bigquery_datasets'] = 0
            self.errors.append(f"BigQuery validation failed: {e}")

        return validation_results

    def run_full_deployment(self) -> Dict[str, Any]:
        """Run the complete GCP resource deployment."""
        print("🚀 Starting Google Cloud Platform Python-Only Deployment")
        print("=" * 60)

        start_time = datetime.now()

        # Deployment steps
        steps = [
            ("Enable GCP APIs", self.enable_gcp_apis),
            ("Create Pub/Sub Topics", self.create_pubsub_topics),
            ("Create Pub/Sub Subscriptions", self.create_pubsub_subscriptions),
            ("Create Storage Buckets", self.create_storage_buckets),
            ("Create BigQuery Datasets", self.create_bigquery_datasets),
            ("Create BigQuery Tables", self.create_bigquery_tables)
        ]

        completed_steps = 0
        for step_name, step_func in steps:
            print(f"\n📋 {step_name}")
            if step_func():
                completed_steps += 1
            else:
                print(f"❌ {step_name} failed")

        # Validate deployment
        validation_results = self.validate_deployment()

        # Generate final report
        end_time = datetime.now()
        report = {
            'timestamp': end_time.isoformat(),
            'duration_seconds': (end_time - start_time).total_seconds(),
            'deployment_complete': completed_steps == len(steps),
            'steps_completed': completed_steps,
            'total_steps': len(steps),
            'results': self.results,
            'validation': validation_results,
            'errors': self.errors,
            'dry_run': self.dry_run
        }

        print("\n" + "=" * 60)
        if report['deployment_complete']:
            print("🎉 GCP DEPLOYMENT COMPLETE!")
            print("✅ All Google Cloud resources have been deployed")
        else:
            print("⚠️  GCP DEPLOYMENT INCOMPLETE")
            print("❌ Some resources may require manual configuration")
            print(f"Completed: {completed_steps}/{len(steps)} steps")

        if self.errors:
            print(f"\n❌ Errors encountered ({len(self.errors)}):")
            for error in self.errors:
                print(f"   • {error}")

        return report

    def save_report(self, report: Dict[str, Any], filename: str = None):
        """Save deployment report to file."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'gcp_deployment_report_{timestamp}.json'

        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        print(f"📄 Report saved to: {filename}")
        return filename

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Google Cloud Platform Python-Only Deployment')
    parser.add_argument('--config-file', help='Path to GCP deployment config file')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--report-file', help='Output report file path')

    args = parser.parse_args()

    print("🛠️  Google Cloud Platform Python-Only Deployment Tool")
    print("Deploying infrastructure for 7taps Analytics...\n")

    deployer = GCPPythonDeployer(
        config_file=args.config_file,
        dry_run=args.dry_run
    )

    report = deployer.run_full_deployment()
    report_file = deployer.save_report(report, args.report_file)

    # Return appropriate exit code
    exit_code = 0 if report['deployment_complete'] else 1
    print(f"\n🔚 Deployment completed with exit code: {exit_code}")

    return exit_code

if __name__ == '__main__':
    sys.exit(main())
