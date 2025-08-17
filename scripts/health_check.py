#!/usr/bin/env python3
"""
Comprehensive Health Check Script
Proactively detects issues before stakeholders encounter them
"""

import json
import sys
from typing import Dict, List, Tuple

import requests


class HealthChecker:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.issues = []
        self.warnings = []

    def check_endpoint(self, endpoint: str, expected_status: int = 200) -> bool:
        """Check if an endpoint is accessible and returns expected status"""
        try:
            response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
            if response.status_code == expected_status:
                return True
            else:
                self.issues.append(
                    f"Endpoint {endpoint} returned {response.status_code}, expected {expected_status}"
                )
                return False
        except Exception as e:
            self.issues.append(f"Endpoint {endpoint} failed: {str(e)}")
            return False

    def check_post_endpoint(
        self, endpoint: str, data: Dict, expected_status: int = 200
    ) -> bool:
        """Check if a POST endpoint is accessible and returns expected status"""
        try:
            response = requests.post(
                f"{self.base_url}{endpoint}",
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=5,
            )
            if response.status_code == expected_status:
                return True
            else:
                self.issues.append(
                    f"POST endpoint {endpoint} returned {response.status_code}, expected {expected_status}"
                )
                return False
        except Exception as e:
            self.issues.append(f"POST endpoint {endpoint} failed: {str(e)}")
            return False

    def check_dashboard_errors(self) -> bool:
        """Check for dashboard template errors"""
        try:
            response = requests.get(f"{self.base_url}/ui/dashboard", timeout=5)
            if response.status_code == 200:
                content = response.text
                if "ZeroDivisionError" in content or "Internal Server Error" in content:
                    self.issues.append("Dashboard contains template errors")
                    return False
                return True
            else:
                self.issues.append(f"Dashboard returned {response.status_code}")
                return False
        except Exception as e:
            self.issues.append(f"Dashboard check failed: {str(e)}")
            return False

    def check_nlp_functionality(self) -> bool:
        """Check NLP endpoint functionality"""
        test_query = {"query": "Show me recent activity"}
        return self.check_post_endpoint("/api/ui/nlp-query", test_query)

    def check_orchestrator_progress(self) -> bool:
        """Check orchestrator progress endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/debug/progress", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if "modules" in data and "overall_progress" in data:
                    return True
                else:
                    self.warnings.append(
                        "Orchestrator progress endpoint missing expected fields"
                    )
                    return False
            else:
                self.issues.append(
                    f"Orchestrator progress returned {response.status_code}"
                )
                return False
        except Exception as e:
            self.issues.append(f"Orchestrator progress check failed: {str(e)}")
            return False

    def run_comprehensive_check(self) -> Tuple[bool, List[str], List[str]]:
        """Run comprehensive health check"""
        print("🔍 Running comprehensive health check...")

        # Core endpoints
        self.check_endpoint("/health")
        self.check_endpoint("/ui/dashboard")
        self.check_endpoint("/ui/db-terminal")
        self.check_endpoint("/ui/admin")

        # API endpoints
        self.check_endpoint("/api/debug/progress")
        self.check_endpoint("/api/debug/test-report")
        self.check_endpoint("/api/dashboard/metrics")

        # POST endpoints
        self.check_nlp_functionality()

        # Special checks
        self.check_dashboard_errors()
        self.check_orchestrator_progress()

        success = len(self.issues) == 0
        return success, self.issues, self.warnings

    def print_report(self, success: bool, issues: List[str], warnings: List[str]):
        """Print comprehensive health check report"""
        print("\n" + "=" * 60)
        print("🏥 HEALTH CHECK REPORT")
        print("=" * 60)

        if success:
            print("✅ SYSTEM HEALTHY - All checks passed!")
        else:
            print("❌ SYSTEM ISSUES DETECTED")

        if issues:
            print(f"\n🚨 ISSUES ({len(issues)}):")
            for i, issue in enumerate(issues, 1):
                print(f"  {i}. {issue}")

        if warnings:
            print(f"\n⚠️  WARNINGS ({len(warnings)}):")
            for i, warning in enumerate(warnings, 1):
                print(f"  {i}. {warning}")

        if not issues and not warnings:
            print("\n🎉 All systems operational!")

        print("=" * 60)


def main():
    """Main health check function"""
    checker = HealthChecker()
    success, issues, warnings = checker.run_comprehensive_check()
    checker.print_report(success, issues, warnings)

    if not success:
        sys.exit(1)
    else:
        print("\n🚀 System ready for stakeholder demo!")


if __name__ == "__main__":
    main()
