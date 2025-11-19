# ============================================================================
# MONITORING AGENT TESTS
# ============================================================================
from execution_models import WorkflowExecution
from executor_engine import MonitoringAgent
from unittest.mock import Mock, patch
from datetime import datetime

import pytest

class TestMonitoringAgent:
    """Test suite for Monitoring Agent"""
    
    def test_initialization(self, mock_llm):
        """Test monitoring agent initializes correctly"""
        monitor = MonitoringAgent(mock_llm)
        
        assert monitor.llm == mock_llm
        assert len(monitor.active_workflows) == 0
        assert len(monitor.monitoring_tasks) == 0
    
    def test_register_workflow(self, mock_llm):
        """Test registering workflow for monitoring"""
        monitor = MonitoringAgent(mock_llm)
        
        workflow = WorkflowExecution(
            workflow_id="WF-001",
            patient_id="PT123",
            patient_name="John Doe",
            consultation_id="CONS-001",
            started_at=datetime.now()
        )
        
        monitor.register_workflow(workflow)
        
        assert "WF-001" in monitor.active_workflows
        assert monitor.active_workflows["WF-001"] == workflow
    
    @pytest.mark.asyncio
    async def test_monitor_lab_results(self, mock_llm):
        """Test monitoring lab results"""
        monitor = MonitoringAgent(mock_llm)
        
        workflow = WorkflowExecution(
            workflow_id="WF-002",
            patient_id="PT123",
            patient_name="John Doe",
            consultation_id="CONS-002",
            started_at=datetime.now()
        )
        monitor.register_workflow(workflow)
        
        # This will simulate receiving lab results
        with patch('asyncio.sleep', return_value=None):
            results = await monitor.monitor_lab_results("WF-002", "ACT-001")
            
            assert results is not None
            assert "test" in results
    
    @pytest.mark.asyncio
    async def test_alert_physician(self, mock_llm):
        """Test physician alert generation"""
        monitor = MonitoringAgent(mock_llm)
        
        workflow = WorkflowExecution(
            workflow_id="WF-003",
            patient_id="PT123",
            patient_name="John Doe",
            consultation_id="CONS-003",
            started_at=datetime.now()
        )
        monitor.register_workflow(workflow)
        
        await monitor.alert_physician(
            "WF-003",
            "Abnormal Lab Results",
            "Patient has abnormal elevated glucose levels"
        )
        
        assert len(workflow.alerts) == 1
        assert workflow.alerts[0]["type"] == "Abnormal Lab Results"
        assert workflow.alerts[0]["priority"] == "high"