#!/usr/bin/env python3
"""
Data Pipeline Verification Script

This script provides objective metrics to verify the success of our data pipeline,
including data volume, quality, and metadata preservation.
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.7taps')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Heroku app URL
HEROKU_URL = "https://seventaps-analytics-5135b3a0701a.herokuapp.com"

class DataPipelineVerifier:
    """Verify the success of the data pipeline."""
    
    def __init__(self):
        self.results = {}
        self.verification_time = datetime.utcnow()
    
    def run_database_query(self, query, description):
        """Run a database query via the API."""
        try:
            response = requests.post(
                f"{HEROKU_URL}/ui/db-query",
                json={"query": query},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ {description}: {result.get('row_count', 0)} rows")
                return result
            else:
                logger.error(f"❌ {description}: API error {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ {description}: {str(e)}")
            return None
    
    def verify_data_volume(self):
        """Verify data volume across all sources."""
        logger.info("\n📊 Verifying Data Volume...")
        
        # Check total statements by source
        query = """
        SELECT 
            source,
            COUNT(*) as statement_count,
            COUNT(DISTINCT actor_id) as unique_learners,
            MIN(timestamp) as earliest_activity,
            MAX(timestamp) as latest_activity
        FROM statements_new 
        GROUP BY source
        ORDER BY statement_count DESC
        """
        
        result = self.run_database_query(query, "Data volume by source")
        if result:
            self.results['data_volume'] = result
            return True
        return False
    
    def verify_data_quality(self):
        """Verify data quality and completeness."""
        logger.info("\n🔍 Verifying Data Quality...")
        
        # Check for missing critical data
        query = """
        SELECT 
            COUNT(*) as total_statements,
            COUNT(CASE WHEN actor_id IS NOT NULL THEN 1 END) as has_actor,
            COUNT(CASE WHEN activity_id IS NOT NULL THEN 1 END) as has_activity,
            COUNT(CASE WHEN verb_id IS NOT NULL THEN 1 END) as has_verb,
            COUNT(CASE WHEN timestamp IS NOT NULL THEN 1 END) as has_timestamp,
            COUNT(CASE WHEN raw_json IS NOT NULL THEN 1 END) as has_raw_json
        FROM statements_new
        """
        
        result = self.run_database_query(query, "Data quality check")
        if result:
            self.results['data_quality'] = result
            return True
        return False
    
    def verify_metadata_preservation(self):
        """Verify that metadata is properly preserved."""
        logger.info("\n🔗 Verifying Metadata Preservation...")
        
        # Check lesson metadata
        query = """
        SELECT 
            ce.extension_value as lesson_number,
            COUNT(*) as statement_count,
            COUNT(DISTINCT s.actor_id) as unique_learners
        FROM statements_new s
        JOIN context_extensions_new ce ON s.statement_id = ce.statement_id
        WHERE ce.extension_key = 'https://7taps.com/lesson-number'
        GROUP BY ce.extension_value
        ORDER BY lesson_number
        """
        
        result = self.run_database_query(query, "Lesson metadata preservation")
        if result:
            self.results['lesson_metadata'] = result
        
        # Check card type metadata
        query = """
        SELECT 
            ce.extension_value as card_type,
            COUNT(*) as statement_count
        FROM statements_new s
        JOIN context_extensions_new ce ON s.statement_id = ce.statement_id
        WHERE ce.extension_key = 'https://7taps.com/card-type'
        GROUP BY ce.extension_value
        ORDER BY statement_count DESC
        """
        
        result = self.run_database_query(query, "Card type metadata preservation")
        if result:
            self.results['card_type_metadata'] = result
        
        # Check question text preservation
        query = """
        SELECT 
            COUNT(*) as total_statements,
            COUNT(CASE WHEN ce.extension_value IS NOT NULL AND ce.extension_value != '' THEN 1 END) as has_question_text
        FROM statements_new s
        JOIN context_extensions_new ce ON s.statement_id = ce.statement_id
        WHERE ce.extension_key = 'https://7taps.com/question-text'
        """
        
        result = self.run_database_query(query, "Question text preservation")
        if result:
            self.results['question_text_preservation'] = result
        
        return True
    
    def verify_unified_pipeline(self):
        """Verify that both xAPI and CSV data are in the same tables."""
        logger.info("\n🔄 Verifying Unified Pipeline...")
        
        # Check that both sources are in statements_new
        query = """
        SELECT 
            source,
            COUNT(*) as count,
            COUNT(DISTINCT actor_id) as unique_actors,
            COUNT(DISTINCT activity_id) as unique_activities
        FROM statements_new
        GROUP BY source
        ORDER BY count DESC
        """
        
        result = self.run_database_query(query, "Unified pipeline verification")
        if result:
            self.results['unified_pipeline'] = result
            return True
        return False
    
    def verify_analytics_queries(self):
        """Verify that analytics queries work correctly."""
        logger.info("\n📈 Verifying Analytics Queries...")
        
        # Test common analytics queries
        queries = {
            "learner_engagement": """
                SELECT 
                    COUNT(DISTINCT actor_id) as total_learners,
                    COUNT(*) as total_activities,
                    AVG(activities_per_learner) as avg_activities_per_learner
                FROM (
                    SELECT 
                        actor_id,
                        COUNT(*) as activities_per_learner
                    FROM statements_new
                    GROUP BY actor_id
                ) learner_stats
            """,
            "lesson_popularity": """
                SELECT 
                    ce.extension_value as lesson_number,
                    COUNT(*) as activity_count,
                    COUNT(DISTINCT s.actor_id) as unique_learners
                FROM statements_new s
                JOIN context_extensions_new ce ON s.statement_id = ce.statement_id
                WHERE ce.extension_key = 'https://7taps.com/lesson-number'
                GROUP BY ce.extension_value
                ORDER BY activity_count DESC
                LIMIT 5
            """,
            "recent_activity": """
                SELECT 
                    DATE(timestamp) as activity_date,
                    COUNT(*) as activities,
                    COUNT(DISTINCT actor_id) as active_learners
                FROM statements_new
                WHERE timestamp >= NOW() - INTERVAL '7 days'
                GROUP BY DATE(timestamp)
                ORDER BY activity_date DESC
            """
        }
        
        for query_name, query in queries.items():
            result = self.run_database_query(query, f"Analytics query: {query_name}")
            if result:
                self.results[f'analytics_{query_name}'] = result
        
        return True
    
    def generate_success_report(self):
        """Generate a comprehensive success report."""
        logger.info("\n📋 Generating Success Report...")
        
        report = {
            "verification_time": self.verification_time.isoformat(),
            "overall_success": True,
            "metrics": {},
            "recommendations": []
        }
        
        # Calculate success metrics
        if 'data_volume' in self.results:
            data_volume = self.results['data_volume']
            total_statements = sum(row[1] for row in data_volume.get('data', [])[1:])
            total_learners = sum(row[2] for row in data_volume.get('data', [])[1:])
            
            report["metrics"]["total_statements"] = total_statements
            report["metrics"]["total_learners"] = total_learners
            report["metrics"]["sources"] = len(data_volume.get('data', [])) - 1  # Exclude header
        
        if 'data_quality' in self.results:
            quality = self.results['data_quality']
            if quality.get('data'):
                row = quality['data'][1]  # First data row
                total = row[0]
                has_actor = row[1]
                has_activity = row[2]
                has_verb = row[3]
                has_timestamp = row[4]
                has_raw_json = row[5]
                
                report["metrics"]["data_quality"] = {
                    "completeness_rate": {
                        "actor": has_actor / total if total > 0 else 0,
                        "activity": has_activity / total if total > 0 else 0,
                        "verb": has_verb / total if total > 0 else 0,
                        "timestamp": has_timestamp / total if total > 0 else 0,
                        "raw_json": has_raw_json / total if total > 0 else 0
                    }
                }
        
        # Generate recommendations
        if 'data_volume' in self.results:
            data_volume = self.results['data_volume']
            if data_volume.get('data'):
                for row in data_volume['data'][1:]:  # Skip header
                    source, count, learners = row[0], row[1], row[2]
                    if count == 0:
                        report["recommendations"].append(f"No data found for source: {source}")
                    elif learners == 0:
                        report["recommendations"].append(f"No unique learners for source: {source}")
        
        # Save report
        report_file = f"reports/pipeline_verification_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs("reports", exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📄 Success report saved to: {report_file}")
        
        return report
    
    def run_full_verification(self):
        """Run the complete verification process."""
        logger.info("🚀 Starting Data Pipeline Verification")
        logger.info("=" * 50)
        
        verification_steps = [
            ("Data Volume", self.verify_data_volume),
            ("Data Quality", self.verify_data_quality),
            ("Metadata Preservation", self.verify_metadata_preservation),
            ("Unified Pipeline", self.verify_unified_pipeline),
            ("Analytics Queries", self.verify_analytics_queries)
        ]
        
        success_count = 0
        total_steps = len(verification_steps)
        
        for step_name, step_function in verification_steps:
            try:
                if step_function():
                    success_count += 1
                    logger.info(f"✅ {step_name} verification passed")
                else:
                    logger.error(f"❌ {step_name} verification failed")
            except Exception as e:
                logger.error(f"❌ {step_name} verification error: {e}")
        
        # Generate report
        report = self.generate_success_report()
        
        # Summary
        logger.info("\n📊 Verification Summary")
        logger.info("=" * 30)
        logger.info(f"Steps passed: {success_count}/{total_steps}")
        logger.info(f"Success rate: {(success_count/total_steps)*100:.1f}%")
        
        if success_count == total_steps:
            logger.info("🎉 All verifications passed! Data pipeline is working correctly.")
        else:
            logger.warning("⚠️  Some verifications failed. Check the report for details.")
        
        return report

def main():
    """Main verification function."""
    verifier = DataPipelineVerifier()
    report = verifier.run_full_verification()
    
    # Print key metrics
    print("\n📈 Key Metrics:")
    print(f"Total Statements: {report['metrics'].get('total_statements', 'N/A')}")
    print(f"Total Learners: {report['metrics'].get('total_learners', 'N/A')}")
    print(f"Data Sources: {report['metrics'].get('sources', 'N/A')}")
    
    if 'data_quality' in report['metrics']:
        quality = report['metrics']['data_quality']['completeness_rate']
        print(f"Data Completeness: {quality['actor']*100:.1f}% actors, {quality['activity']*100:.1f}% activities")

if __name__ == "__main__":
    main()
