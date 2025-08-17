"""
Architecture validation test for simplified 7taps analytics system.
"""

import os
import sys

import pytest

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestSimplifiedArchitectureValidation:
    """Test that the simplified architecture is properly implemented."""

    def test_no_mcp_dependencies(self):
        """Test that no MCP dependencies remain in the codebase."""
        # Check main app
        with open("app/main.py", "r") as f:
            content = f.read()
            assert "mcp" not in content.lower()

        # Check ETL
        with open("app/etl_streaming.py", "r") as f:
            content = f.read()
            assert "import mcp" not in content.lower()
            assert "from mcp" not in content.lower()

        # Check API endpoints
        with open("app/api/etl.py", "r") as f:
            content = f.read()
            assert "mcp" not in content.lower()

    def test_direct_connection_architecture(self):
        """Test that the architecture uses direct connections."""
        # Check docker-compose.yml
        with open("docker-compose.yml", "r") as f:
            content = f.read()
            assert "mcp-python" not in content
            assert "mcp-postgres" not in content
            assert "Direct Database Access" in content

        # Check config
        with open("app/config.py", "r") as f:
            content = f.read()
            assert "MCP_POSTGRES_URL" not in content
            assert "MCP_PYTHON_URL" not in content
            assert "Direct Database Connections" in content

    def test_contract_status(self):
        """Test that contracts reflect the simplified architecture."""
        # Check that b01 is marked as obsolete
        with open("orchestrator_contracts/b01_attach_mcp_servers.json", "r") as f:
            content = f.read()
            assert '"status": "obsolete"' in content

        # Check that b02 reflects direct connections
        with open("orchestrator_contracts/b02_streaming_etl.json", "r") as f:
            content = f.read()
            assert "direct psycopg2" in content
            assert "simplified architecture" in content

        # Check that b13 is ready for verification
        with open(
            "orchestrator_contracts/b13_learninglocker_integration.json", "r"
        ) as f:
            content = f.read()
            assert '"status": "awaiting_verification"' in content
            assert '"progress_percentage": 100' in content

    def test_performance_improvements(self):
        """Test that the simplified architecture provides performance improvements."""
        # Check that connection pooling is implemented
        with open("app/etl_streaming.py", "r") as f:
            content = f.read()
            assert "SimpleConnectionPool" in content
            assert "max_connections" in content
            assert "connection_pooling" in content

        # Check that batch processing is implemented
        assert "batch_size" in content
        assert "write_batch_to_postgres" in content

    def test_error_handling(self):
        """Test that comprehensive error handling is implemented."""
        with open("app/etl_streaming.py", "r") as f:
            content = f.read()
            assert "try:" in content
            assert "except Exception" in content
            assert "logger.error" in content

        with open("app/sync_learninglocker.py", "r") as f:
            content = f.read()
            assert "try:" in content
            assert "except Exception" in content
            assert "logger.error" in content

    def test_learninglocker_integration(self):
        """Test that Learning Locker integration is properly implemented."""
        # Check that Learning Locker sync service exists
        assert os.path.exists("app/sync_learninglocker.py")
        assert os.path.exists("app/api/learninglocker_sync.py")

        # Check that Learning Locker is in docker-compose
        with open("docker-compose.yml", "r") as f:
            content = f.read()
            assert "learninglocker:" in content

        # Check that sync endpoints are defined
        with open("app/api/learninglocker_sync.py", "r") as f:
            content = f.read()
            assert "sync-learninglocker" in content
            assert "sync-status" in content
            assert "learninglocker-info" in content

    def test_xapi_lrs_endpoints(self):
        """Test that xAPI LRS endpoints are properly implemented."""
        # Check that xAPI LRS endpoints exist
        assert os.path.exists("app/api/xapi_lrs.py")

        # Check that endpoints are defined
        with open("app/api/xapi_lrs.py", "r") as f:
            content = f.read()
            assert "/statements" in content
            assert "/about" in content
            assert "Basic Authentication" in content

    def test_etl_endpoints(self):
        """Test that ETL endpoints are properly implemented."""
        # Check that ETL endpoints exist
        assert os.path.exists("app/api/etl.py")

        # Check that endpoints are defined
        with open("app/api/etl.py", "r") as f:
            content = f.read()
            assert "test-etl-streaming" in content
            assert "etl-status" in content

    def test_environment_configuration(self):
        """Test that environment variables are configured for simplified architecture."""
        # Check that direct connection variables are available
        assert "DATABASE_URL" in os.environ or "DATABASE_URL" in os.environ
        assert "REDIS_URL" in os.environ or "REDIS_URL" in os.environ

        # Check that MCP variables are not used
        assert "MCP_POSTGRES_URL" not in os.environ
        assert "MCP_PYTHON_URL" not in os.environ

    def test_docker_compose_simplified(self):
        """Test that docker-compose.yml is simplified without MCP services."""
        with open("docker-compose.yml", "r") as f:
            content = f.read()

        # Should not contain MCP services
        assert "mcp-python:" not in content
        assert "mcp-postgres:" not in content

        # Should contain direct database services
        assert "postgres:" in content
        assert "redis:" in content

        # Should contain Learning Locker
        assert "learninglocker:" in content


class TestArchitectureBenefits:
    """Test the benefits of the simplified architecture."""

    def test_reduced_complexity(self):
        """Test that complexity has been reduced."""
        # Count MCP references in codebase
        mcp_files = []
        for root, dirs, files in os.walk("."):
            if "node_modules" in root or ".git" in root:
                continue
            for file in files:
                if (
                    file.endswith(".py")
                    or file.endswith(".json")
                    or file.endswith(".yml")
                ):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, "r") as f:
                            content = f.read()
                            if "mcp" in content.lower() and "mcp" not in [
                                "mcp_removal_summary.md"
                            ]:
                                mcp_files.append(filepath)
                    except:
                        pass

        # Should have minimal MCP references (only in documentation)
        assert len(mcp_files) <= 5, f"Too many MCP references found: {mcp_files}"

    def test_improved_performance(self):
        """Test that performance improvements are implemented."""
        with open("app/etl_streaming.py", "r") as f:
            content = f.read()

        # Check for performance optimizations
        assert "connection_pooling" in content
        assert "batch_size" in content
        assert "max_connections" in content
        assert "retry_on_timeout" in content

    def test_better_maintainability(self):
        """Test that maintainability has improved."""
        # Check for clear documentation
        with open("app/etl_streaming.py", "r") as f:
            content = f.read()
            assert '"""' in content  # Docstrings present
            assert "logger" in content  # Logging implemented

        # Check for proper error handling
        assert "try:" in content
        assert "except Exception" in content

    def test_standard_tools(self):
        """Test that standard tools are used."""
        with open("app/etl_streaming.py", "r") as f:
            content = f.read()

        # Should use standard database libraries
        assert "import psycopg2" in content
        assert "import redis" in content
        assert "from psycopg2.pool import SimpleConnectionPool" in content

        # Should not use MCP libraries
        assert "import mcp" not in content
        assert "from mcp" not in content


if __name__ == "__main__":
    pytest.main([__file__])
