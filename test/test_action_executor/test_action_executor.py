# ============================================================================
# ACTION EXECUTOR TESTS
# ============================================================================
import pytest
from unittest.mock import Mock, patch
from executor_engine.action_executor import ActionExecutor
from  execution_models.models import ActionExecution, ExecutionStatus



class TestActionExecutor:
    """Test suite for Action Executor"""
    
    @pytest.mark.asyncio
    async def test_execute_lab_order(self, sample_action_execution):
        """Test executing lab order"""
        executor = ActionExecutor()
        
        result = await executor.execute_lab_order(sample_action_execution)
        
        assert result["status"] == "ordered"
        assert "order_id" in result
        assert "confirmation" in result
        assert "scheduled_date" in result
        assert "lab_facility" in result
    
    @pytest.mark.asyncio
    async def test_execute_imaging_order(self):
        """Test executing imaging order"""
        executor = ActionExecutor()
        
        action = ActionExecution(
            action_id="ACT-002",
            action_type="imaging",
            description="Order lumbar spine MRI",
            status=ExecutionStatus.PENDING
        )
        
        result = await executor.execute_imaging_order(action)
        
        assert result["status"] == "ordered"
        assert result["modality"] == "MRI"
        assert "order_id" in result
        assert "imaging_center" in result
    
    @pytest.mark.asyncio
    async def test_execute_referral(self):
        """Test executing specialist referral"""
        executor = ActionExecutor()
        
        action = ActionExecution(
            action_id="ACT-003",
            action_type="referral",
            description="Refer to cardiologist",
            status=ExecutionStatus.PENDING
        )
        
        result = await executor.execute_referral(action)
        
        assert result["status"] == "pending"
        assert "referral_id" in result
        assert "specialist" in result
    
    @pytest.mark.asyncio
    async def test_execute_medication(self):
        """Test executing medication prescription"""
        executor = ActionExecutor()
        
        action = ActionExecution(
            action_id="ACT-004",
            action_type="medication",
            description="Lisinopril 10mg daily",
            status=ExecutionStatus.PENDING
        )
        
        result = await executor.execute_medication(action)
        
        assert result["status"] == "sent_to_pharmacy"
        assert "prescription_id" in result
        assert "pharmacy" in result
        assert "ready_for_pickup" in result
    
    @pytest.mark.asyncio
    async def test_execute_follow_up(self):
        """Test scheduling follow-up appointment"""
        executor = ActionExecutor()
        
        action = ActionExecution(
            action_id="ACT-005",
            action_type="follow-up",
            description="Follow-up in 2 weeks",
            status=ExecutionStatus.PENDING
        )
        
        result = await executor.execute_follow_up(action)
        
        assert result["status"] == "scheduled"
        assert "appointment_id" in result
        assert "date" in result
        assert result["confirmation_sent"] == True
    
    @pytest.mark.asyncio
    async def test_execute_action_updates_status(self, sample_action_execution):
        """Test that execute_action updates action status"""
        executor = ActionExecutor()
        
        result = await executor.execute_action(sample_action_execution)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.executed_time is not None
        assert result.result is not None
    
    @pytest.mark.asyncio
    async def test_execute_action_handles_error(self):
        """Test error handling in execute_action"""
        executor = ActionExecutor()
        
        # Create action with invalid type to trigger error path
        action = ActionExecution(
            action_id="ACT-999",
            action_type="invalid_type",
            description="This should work gracefully",
            status=ExecutionStatus.PENDING
        )
        
        # Mock one of the methods to raise an exception
        with patch.object(executor, 'execute_lab_order', side_effect=Exception("API Error")):
            action.action_type = "lab"
            result = await executor.execute_action(action)
            
            assert result.status == ExecutionStatus.FAILED
            assert result.error is not None
