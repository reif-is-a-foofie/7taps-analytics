"""
Orchestrator API endpoints for monitoring multi-agent development progress.

This module provides debug endpoints for tracking module assignments, test results,
and active agents in the 7taps analytics development system.
"""

import os
import json
import glob
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path

router = APIRouter()

class OrchestratorTracker:
    """Tracks orchestrator contracts and agent progress."""
    
    def __init__(self):
        self.contracts_dir = "orchestrator_contracts"
        self.contracts = {}
        self.mcp_call_log = []
        self.module_assignments = []
        self.test_results = []
        self.load_contracts()
    
    def load_contracts(self):
        """Load all contract files from orchestrator_contracts directory."""
        contract_files = glob.glob(f"{self.contracts_dir}/*.json")
        
        for contract_file in contract_files:
            try:
                with open(contract_file, 'r') as f:
                    contract = json.load(f)
                    module_name = contract.get('module', 'unknown')
                    self.contracts[module_name] = contract
            except Exception as e:
                print(f"Error loading contract {contract_file}: {e}")
    
    def get_all_contracts(self) -> Dict[str, Any]:
        """Get all contracts with their current status."""
        return self.contracts
    
    def get_active_agents(self) -> List[Dict[str, Any]]:
        """Get list of currently active agents and their modules."""
        active_agents = []
        
        for module_name, contract in self.contracts.items():
            status = contract.get('status', 'unknown')
            if status in ['assigned', 'in_progress']:
                agent = contract.get('agent', 'unknown')
                progress = contract.get('task_tracking', {}).get('progress_percentage', 0)
                
                active_agents.append({
                    'module': module_name,
                    'agent': agent,
                    'status': status,
                    'progress_percentage': progress,
                    'assigned_at': contract.get('task_tracking', {}).get('assigned_at')
                })
        
        return active_agents
    
    def get_test_results(self) -> Dict[str, Any]:
        """Get test results for all modules with anti-spec-gaming validation."""
        test_results = {}
        
        for module_name, contract in self.contracts.items():
            status = contract.get('status', 'unknown')
            test_file = None
            
            # Find test file for this module
            allowed_files = contract.get('allowed_files', [])
            for file_path in allowed_files:
                if 'test_' in file_path and file_path.endswith('.py'):
                    test_file = file_path
                    break
            
            # Determine test requirements
            requires_real_world_testing = self._requires_real_world_testing(module_name)
            
            # Anti-spec-gaming validation
            spec_gaming_risk = self._check_spec_gaming_risk(module_name, contract)
            
            test_results[module_name] = {
                'status': status,
                'test_file': test_file,
                'test_status': 'pending' if status == 'pending' else 'ready_for_validation',
                'requires_real_world_testing': requires_real_world_testing,
                'real_world_test_notes': self._get_real_world_test_notes(module_name),
                'spec_gaming_risk': spec_gaming_risk,
                'requires_independent_validation': spec_gaming_risk['high_risk']
            }
        
        return test_results
    
    def _check_spec_gaming_risk(self, module_name: str, contract: Dict[str, Any]) -> Dict[str, Any]:
        """Check for potential spec-gaming violations."""
        agent = contract.get('agent', 'unknown')
        allowed_files = contract.get('allowed_files', [])
        
        # Check if implementation agent wrote their own tests
        test_files = [f for f in allowed_files if 'test_' in f and f.endswith('.py')]
        self_written_tests = len(test_files) > 0
        
        # Check if agent marked their own module as completed
        self_marked_completed = contract.get('status') == 'completed' and agent != 'orchestrator_agent'
        
        risk_factors = []
        if self_written_tests:
            risk_factors.append("Implementation agent wrote own tests")
        if self_marked_completed:
            risk_factors.append("Implementation agent marked own module completed")
        
        return {
            'high_risk': len(risk_factors) > 0,
            'risk_factors': risk_factors,
            'requires_independent_testing': self_written_tests,
            'requires_orchestrator_review': self_marked_completed
        }
    
    def _requires_real_world_testing(self, module_name: str) -> bool:
        """Determine if a module requires real-world testing."""
        real_world_modules = {
            'b.01_attach_mcp_servers': True,  # Needs actual MCP servers
            'b.02_streaming_etl': True,       # Needs Redis + MCP servers
            'b.03_incremental_etl': True,     # Needs Redis + MCP servers
            'b.04_orchestrator_mcp': False,   # Pure API, unit tests sufficient
            'b.05_nlp_query': True,           # Needs MCP DB + LangChain
            'b.06_ui': True                   # Needs SQLPad/Superset
        }
        return real_world_modules.get(module_name, False)
    
    def _get_real_world_test_notes(self, module_name: str) -> str:
        """Get notes about real-world testing requirements."""
        test_notes = {
            'b.01_attach_mcp_servers': 'Requires docker-compose up with MCP servers running',
            'b.02_streaming_etl': 'Requires Redis Streams + MCP Python + MCP DB servers',
            'b.03_incremental_etl': 'Requires Redis + MCP servers for ETL processing',
            'b.05_nlp_query': 'Requires MCP DB + LangChain/LlamaIndex integration',
            'b.06_ui': 'Requires SQLPad/Superset embedded UI'
        }
        return test_notes.get(module_name, 'Unit tests only')
    
    def log_mcp_call(self, call_type: str, module: str, details: Dict[str, Any]) -> None:
        """Log an MCP call for tracking and monitoring."""
        mcp_call = {
            'timestamp': datetime.utcnow().isoformat(),
            'call_type': call_type,
            'module': module,
            'details': details,
            'status': 'active'
        }
        self.mcp_call_log.append(mcp_call)
        print(f"MCP Call Logged: {call_type} for {module}")
    
    def track_module_assignment(self, module: str, agent: str, status: str) -> None:
        """Track module assignment and status changes."""
        assignment = {
            'timestamp': datetime.utcnow().isoformat(),
            'module': module,
            'agent': agent,
            'status': status,
            'previous_status': self._get_previous_status(module)
        }
        self.module_assignments.append(assignment)
        print(f"Module Assignment Tracked: {module} -> {agent} ({status})")
    
    def log_mcp_call_and_test_result(self, call_type: str, module: str, test_result: Dict[str, Any]) -> None:
        """Log MCP call with associated test result."""
        combined_log = {
            'timestamp': datetime.utcnow().isoformat(),
            'call_type': call_type,
            'module': module,
            'test_result': test_result,
            'status': 'completed'
        }
        self.mcp_call_log.append(combined_log)
        self.test_results.append(test_result)
        print(f"MCP Call + Test Result Logged: {call_type} for {module}")
    
    def log_multiple_mcp_calls(self, calls: List[Dict[str, Any]]) -> None:
        """Log multiple MCP calls in batch."""
        batch_log = {
            'timestamp': datetime.utcnow().isoformat(),
            'batch_size': len(calls),
            'calls': calls,
            'status': 'batch_completed'
        }
        self.mcp_call_log.extend(calls)
        print(f"Multiple MCP Calls Logged: {len(calls)} calls")
    
    def integrate_mcp_call(self, call_data: Dict[str, Any]) -> Dict[str, Any]:
        """Integrate MCP call data with existing tracking."""
        integrated_call = {
            'timestamp': datetime.utcnow().isoformat(),
            'call_data': call_data,
            'contract_status': self._get_contract_status(call_data.get('module', '')),
            'agent_status': self._get_agent_status(call_data.get('agent', '')),
            'status': 'integrated'
        }
        self.mcp_call_log.append(integrated_call)
        return integrated_call
    
    def integrate_test_result(self, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """Integrate test result with MCP call tracking."""
        integrated_result = {
            'timestamp': datetime.utcnow().isoformat(),
            'test_data': test_data,
            'mcp_calls_related': self._get_related_mcp_calls(test_data.get('module', '')),
            'status': 'integrated'
        }
        self.test_results.append(integrated_result)
        return integrated_result
    
    def _get_previous_status(self, module: str) -> str:
        """Get previous status for a module."""
        if module in self.contracts:
            return self.contracts[module].get('status', 'unknown')
        return 'unknown'
    
    def _get_contract_status(self, module: str) -> str:
        """Get current contract status for a module."""
        if module in self.contracts:
            return self.contracts[module].get('status', 'unknown')
        return 'unknown'
    
    def _get_agent_status(self, agent: str) -> str:
        """Get current agent status."""
        active_agents = self.get_active_agents()
        for agent_info in active_agents:
            if agent_info.get('agent') == agent:
                return agent_info.get('status', 'unknown')
        return 'inactive'
    
    def _get_related_mcp_calls(self, module: str) -> List[Dict[str, Any]]:
        """Get MCP calls related to a specific module."""
        related_calls = []
        for call in self.mcp_call_log:
            if call.get('module') == module:
                related_calls.append(call)
        return related_calls

# Request models
class ContractUpdateRequest(BaseModel):
    module: str
    updates: Dict[str, Any]

# Initialize orchestrator tracker
orchestrator_tracker = OrchestratorTracker()

# Expose MCP logging functions at module level for testing
def log_mcp_call(call_type: str, module: str, details: Dict[str, Any]) -> None:
    """Log an MCP call for tracking and monitoring."""
    return orchestrator_tracker.log_mcp_call(call_type, module, details)

def track_module_assignment(module: str, agent: str, status: str) -> None:
    """Track module assignment and status changes."""
    return orchestrator_tracker.track_module_assignment(module, agent, status)

def log_mcp_call_and_test_result(call_type: str, module: str, test_result: Dict[str, Any]) -> None:
    """Log MCP call with associated test result."""
    return orchestrator_tracker.log_mcp_call_and_test_result(call_type, module, test_result)

def log_multiple_mcp_calls(calls: List[Dict[str, Any]]) -> None:
    """Log multiple MCP calls in batch."""
    return orchestrator_tracker.log_multiple_mcp_calls(calls)

def integrate_mcp_call(call_data: Dict[str, Any]) -> Dict[str, Any]:
    """Integrate MCP call data with existing tracking."""
    return orchestrator_tracker.integrate_mcp_call(call_data)

def integrate_test_result(test_data: Dict[str, Any]) -> Dict[str, Any]:
    """Integrate test result with MCP call tracking."""
    return orchestrator_tracker.integrate_test_result(test_data)

@router.get("/debug/progress")
async def get_progress() -> Dict[str, Any]:
    """
    Get progress overview of all modules and their current status.
    
    Returns:
        Dict containing module assignments, test results, and overall progress.
    """
    try:
        contracts = orchestrator_tracker.get_all_contracts()
        
        # Calculate overall progress
        total_modules = len(contracts)
        completed_modules = sum(1 for c in contracts.values() if c.get('status') == 'completed')
        overall_progress = (completed_modules / total_modules * 100) if total_modules > 0 else 0
        
        return {
            "status": "success",
            "module": "b.04_orchestrator_mcp",
            "timestamp": datetime.utcnow().isoformat(),
            "overall_progress": overall_progress,
            "total_modules": total_modules,
            "completed_modules": completed_modules,
            "modules": contracts
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get progress: {str(e)}"
        )

@router.get("/debug/test-report")
async def get_test_report() -> Dict[str, Any]:
    """
    Get test report for all modules.
    
    Returns:
        Dict containing test status for each module.
    """
    try:
        test_results = orchestrator_tracker.get_test_results()
        
        return {
            "status": "success",
            "module": "b.04_orchestrator_mcp",
            "timestamp": datetime.utcnow().isoformat(),
            "test_results": test_results
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get test report: {str(e)}"
        )

@router.get("/debug/active-agents")
async def get_active_agents() -> Dict[str, Any]:
    """
    Get list of currently active agents and their assigned modules.
    
    Returns:
        Dict containing active agents and their current tasks.
    """
    try:
        active_agents = orchestrator_tracker.get_active_agents()
        
        return {
            "status": "success",
            "module": "b.04_orchestrator_mcp",
            "timestamp": datetime.utcnow().isoformat(),
            "active_agents": active_agents,
            "agent_count": len(active_agents)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get active agents: {str(e)}"
        )

@router.get("/debug/real-world-testing")
async def get_real_world_testing_status() -> Dict[str, Any]:
    """
    Get real-world testing requirements and status for all modules.
    
    Returns:
        Dict containing modules that need real-world testing and their requirements.
    """
    try:
        test_results = orchestrator_tracker.get_test_results()
        
        # Filter modules that need real-world testing
        real_world_modules = {}
        for module_name, result in test_results.items():
            if result.get('requires_real_world_testing', False):
                real_world_modules[module_name] = {
                    'status': result['status'],
                    'test_notes': result['real_world_test_notes'],
                    'ready_for_real_world_test': result['status'] in ['completed', 'assigned']
                }
        
        return {
            "status": "success",
            "module": "b.04_orchestrator_mcp",
            "timestamp": datetime.utcnow().isoformat(),
            "real_world_testing_modules": real_world_modules,
            "total_real_world_modules": len(real_world_modules),
            "ready_for_real_world_test": sum(1 for m in real_world_modules.values() if m['ready_for_real_world_test'])
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get real-world testing status: {str(e)}"
        )

@router.get("/debug/anti-spec-gaming")
async def get_anti_spec_gaming_status() -> Dict[str, Any]:
    """
    Get anti-spec-gaming validation status for all modules.
    
    Returns:
        Dict containing spec-gaming risks and required fixes.
    """
    try:
        test_results = orchestrator_tracker.get_test_results()
        
        # Identify spec-gaming violations
        violations = []
        high_risk_modules = []
        
        for module_name, result in test_results.items():
            spec_gaming_risk = result.get('spec_gaming_risk', {})
            if spec_gaming_risk.get('high_risk', False):
                high_risk_modules.append({
                    'module': module_name,
                    'risk_factors': spec_gaming_risk.get('risk_factors', []),
                    'requires_independent_testing': spec_gaming_risk.get('requires_independent_testing', False),
                    'requires_orchestrator_review': spec_gaming_risk.get('requires_orchestrator_review', False)
                })
                violations.extend(spec_gaming_risk.get('risk_factors', []))
        
        return {
            "status": "success",
            "module": "b.04_orchestrator_mcp",
            "timestamp": datetime.utcnow().isoformat(),
            "anti_spec_gaming_status": {
                "total_violations": len(violations),
                "high_risk_modules": len(high_risk_modules),
                "violations": list(set(violations)),  # Unique violations
                "high_risk_modules_details": high_risk_modules,
                "requires_independent_testing_agent": len(high_risk_modules) > 0
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get anti-spec-gaming status: {str(e)}"
        )

@router.post("/debug/update-contract")
async def update_contract(request: ContractUpdateRequest) -> Dict[str, Any]:
    """
    Update a specific contract (for orchestrator use).
    
    Args:
        module: Module name to update
        updates: Dictionary of updates to apply
        
    Returns:
        Updated contract information
    """
    try:
        if request.module not in orchestrator_tracker.contracts:
            raise HTTPException(status_code=404, detail=f"Module {request.module} not found")
        
        contract = orchestrator_tracker.contracts[request.module]
        
        # Apply updates
        for key, value in request.updates.items():
            if key in contract:
                contract[key] = value
            elif key == 'task_tracking':
                contract['task_tracking'].update(value)
        
        # Save updated contract
        contract_file = f"{orchestrator_tracker.contracts_dir}/{request.module}.json"
        with open(contract_file, 'w') as f:
            json.dump(contract, f, indent=2)
        
        return {
            "status": "success",
            "module": request.module,
            "updated_contract": contract
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update contract: {str(e)}"
        )


@router.get("/debug/deployment-status")
async def get_deployment_status() -> Dict[str, Any]:
    """Get comprehensive deployment and streaming infrastructure status."""
    try:
        import subprocess
        import platform
        
        # System information
        system_info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "architecture": platform.machine()
        }
        
        # Docker status
        docker_status = {"available": False, "version": None}
        try:
            result = subprocess.run(
                ["docker", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            if result.returncode == 0:
                docker_status["available"] = True
                docker_status["version"] = result.stdout.strip()
        except Exception:
            pass
        
        # Docker Compose status
        compose_status = {"available": False, "version": None}
        try:
            result = subprocess.run(
                ["docker-compose", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            if result.returncode == 0:
                compose_status["available"] = True
                compose_status["version"] = result.stdout.strip()
        except Exception:
            pass
        
        # Service health checks
        service_health = {}
        services = ["postgres", "redis", "mcp-postgres", "mcp-python", "app"]
        
        for service in services:
            try:
                # Try to connect to service (simplified check)
                service_health[service] = {
                    "status": "unknown",
                    "last_check": datetime.now().isoformat()
                }
            except Exception as e:
                service_health[service] = {
                    "status": "error",
                    "error": str(e),
                    "last_check": datetime.now().isoformat()
                }
        
        # MCP server status
        mcp_status = {
            "mcp_postgres": {
                "url": os.getenv("MCP_POSTGRES_URL", "http://localhost:8001"),
                "status": "unknown"
            },
            "mcp_python": {
                "url": os.getenv("MCP_PYTHON_URL", "http://localhost:8002"),
                "status": "unknown"
            }
        }
        
        # Environment variables
        env_vars = {
            "DATABASE_URL": os.getenv("DATABASE_URL", "not_set"),
            "REDIS_URL": os.getenv("REDIS_URL", "not_set"),
            "MCP_POSTGRES_URL": os.getenv("MCP_POSTGRES_URL", "not_set"),
            "MCP_PYTHON_URL": os.getenv("MCP_PYTHON_URL", "not_set"),
            "LOG_LEVEL": os.getenv("LOG_LEVEL", "info")
        }
        
        # Deployment configuration
        deployment_config = {
            "docker_compose_services": [
                "postgres", "redis", "mcp-postgres", "mcp-python", "sqlpad", "app"
            ],
            "exposed_ports": {
                "app": 8000,
                "postgres": 5432,
                "redis": 6379,
                "mcp-postgres": 8001,
                "mcp-python": 8002,
                "sqlpad": 3000
            },
            "volumes": ["postgres_data", "redis_data", "sqlpad_data", "logs"],
            "health_checks_enabled": True,
            "restart_policy": "unless-stopped"
        }
        
        return {
            "deployment_status": "operational",
            "timestamp": datetime.now().isoformat(),
            "system_info": system_info,
            "docker_status": docker_status,
            "compose_status": compose_status,
            "service_health": service_health,
            "mcp_status": mcp_status,
            "environment_variables": env_vars,
            "deployment_config": deployment_config,
            "recommendations": [
                "All services should be running via docker-compose up",
                "MCP servers should be accessible on their respective ports",
                "Health checks should be passing for all services",
                "Logs should be monitored for any errors"
            ]
        }
        
    except Exception as e:
        return {
            "deployment_status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "message": "Failed to retrieve deployment status"
        } 