#!/usr/bin/env python3
"""
Test deployment locally before deploying to Cloud Run.
This script helps debug deployment issues by testing the container locally.
"""

import os
import subprocess
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_app_startup():
    """Test if the app starts up correctly locally."""
    logger.info("Testing app startup locally...")

    try:
        # Set PORT environment variable like Cloud Run does
        env = os.environ.copy()
        env['PORT'] = '8080'

        # Start the app
        process = subprocess.Popen(
            ['uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8080', '--workers', '1'],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Give it time to start
        time.sleep(5)

        # Test health endpoint
        import requests
        try:
            response = requests.get('http://localhost:8080/api/health', timeout=10)
            if response.status_code == 200:
                logger.info("✅ Health check passed")
                return True
            else:
                logger.error(f"❌ Health check failed: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Could not connect to health endpoint: {e}")
            return False
        finally:
            process.terminate()
            process.wait()

    except Exception as e:
        logger.error(f"❌ App startup test failed: {e}")
        return False

def test_docker_build():
    """Test if Docker build works."""
    logger.info("Testing Docker build...")

    try:
        # Build the image
        build_cmd = [
            'docker', 'build',
            '-f', 'config/Dockerfile',
            '-t', '7taps-analytics-test',
            '.'
        ]

        logger.info(f"Running: {' '.join(build_cmd)}")

        result = subprocess.run(build_cmd, capture_output=True, text=True, timeout=600)

        if result.returncode == 0:
            logger.info("✅ Docker build successful")
            return True
        else:
            logger.error("❌ Docker build failed")
            logger.error(f"STDOUT: {result.stdout}")
            logger.error(f"STDERR: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("❌ Docker build timed out")
        return False
    except Exception as e:
        logger.error(f"❌ Docker build error: {e}")
        return False

def test_docker_run():
    """Test if Docker container runs correctly."""
    logger.info("Testing Docker container...")

    try:
        # Run the container
        run_cmd = [
            'docker', 'run',
            '-p', '8080:8080',
            '-e', 'PORT=8080',
            '--rm',
            '7taps-analytics-test'
        ]

        logger.info(f"Running: {' '.join(run_cmd)}")

        # Start container in background
        process = subprocess.Popen(run_cmd)

        # Give it time to start
        time.sleep(10)

        # Test health endpoint
        import requests
        try:
            response = requests.get('http://localhost:8080/api/health', timeout=10)
            if response.status_code == 200:
                logger.info("✅ Docker container health check passed")
                return True
            else:
                logger.error(f"❌ Docker container health check failed: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Could not connect to Docker container: {e}")
            return False
        finally:
            process.terminate()
            process.wait()

    except Exception as e:
        logger.error(f"❌ Docker run test failed: {e}")
        return False

def main():
    """Run all deployment tests."""
    logger.info("🔍 Starting deployment debugging tests...")

    tests = [
        ("App Startup", test_app_startup),
        ("Docker Build", test_docker_build),
        ("Docker Run", test_docker_run),
    ]

    results = []
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running: {test_name}")
        logger.info('='*50)

        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))

    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("📊 TEST SUMMARY")
    logger.info('='*50)

    all_passed = True
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        if not result:
            all_passed = False

    if all_passed:
        logger.info("\n🎉 All tests passed! Ready for Cloud Run deployment.")
        return True
    else:
        logger.error("\n⚠️  Some tests failed. Please fix issues before deploying to Cloud Run.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

