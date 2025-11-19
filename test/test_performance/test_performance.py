# ============================================================================
# PERFORMANCE TESTS
# ============================================================================
from datetime import datetime
from executor_engine import ActionExecutor
from execution_models import ActionExecution, ExecutionStatus

import asyncio
import pytest

class TestPerformance:
    """Performance and stress tests"""
    
    @pytest.mark.asyncio
    async def test_action_execution_speed(self):
        """Test that action execution completes within acceptable time"""
        executor = ActionExecutor()
        
        action = ActionExecution(
            action_id="PERF-001",
            action_type="lab",
            description="Performance test lab order",
            status=ExecutionStatus.PENDING
        )
        
        start_time = datetime.now()
        result = await executor.execute_action(action)
        duration = (datetime.now() - start_time).total_seconds()
        
        # Should complete in under 5 seconds (simulated delay is 1 second)
        assert duration < 5
        assert result.status == ExecutionStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_bulk_action_execution(self):
        """Test executing many actions"""
        executor = ActionExecutor()
        
        actions = [
            ActionExecution(
                action_id=f"BULK-{i:03d}",
                action_type="lab",
                description=f"Bulk test {i}",
                status=ExecutionStatus.PENDING
            )
            for i in range(50)
        ]
        
        start_time = datetime.now()
        results = await asyncio.gather(*[
            executor.execute_action(action) 
            for action in actions
        ])
        duration = (datetime.now() - start_time).total_seconds()
        
        assert len(results) == 50
        assert all(r.status == ExecutionStatus.COMPLETED for r in results)
        # Should complete in reasonable time (50 concurrent 1-second operations)
        assert duration < 10