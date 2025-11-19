# ============================================================================
# COMPLETE EXECUTION ENGINE
# ============================================================================
from typing import Dict
from datetime import datetime
import asyncio
from execution_models.models import ActionExecution, ExecutionStatus, WorkflowExecution
from executor_engine.action_executor import ActionExecutor
from executor_engine.monitor_agent import MonitoringAgent
from executor_engine.physician_approval_handler import PhysicianApprovalHandler
from langchain_openai import ChatOpenAI


class HealthcareExecutionEngine:
    """
    Complete execution engine that orchestrates agents, executes actions,
    handles approvals, and provides continuous monitoring.
    """
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.executor = ActionExecutor()
        self.monitor = MonitoringAgent(llm)
        self.approval_handler = PhysicianApprovalHandler()
        self.workflows: Dict[str, WorkflowExecution] = {}
        
    async def execute_workflow(
        self,
        workflow_state: Dict,
        auto_approve: bool = False
    ) -> WorkflowExecution:
        """
        Execute the complete workflow with actions and monitoring
        """
        
        # Create workflow execution tracking
        workflow_id = f"WF-{datetime.now().timestamp()}"
        consultation = workflow_state["consultation"]
        
        workflow = WorkflowExecution(
            workflow_id=workflow_id,
            patient_id=consultation.patient_id,
            patient_name=consultation.patient_name,
            consultation_id=f"CONS-{datetime.now().timestamp()}",
            started_at=datetime.now(),
            status=ExecutionStatus.IN_PROGRESS
        )
        
        self.workflows[workflow_id] = workflow
        
        print(f"\n{'='*60}")
        print(f"🚀 EXECUTION ENGINE - Starting Workflow {workflow_id}")
        print(f"{'='*60}\n")
        
        # 1. Store clinical summary
        clinical_summary = workflow_state.get("clinical_summary")
        if clinical_summary:
            workflow.clinical_summary_id = f"CS-{datetime.now().timestamp()}"
            print(f"✅ Clinical summary stored: {workflow.clinical_summary_id}")
        
        # 2. Convert next steps to executable actions
        next_steps = workflow_state.get("next_steps", [])
        for idx, step in enumerate(next_steps):
            action = ActionExecution(
                action_id=f"ACT-{workflow_id}-{idx}",
                action_type=step.action_type,
                description=step.description,
                status=ExecutionStatus.PENDING,
                requires_physician_approval=step.priority == "high"
            )
            workflow.actions.append(action)
        
        # 3. Check if physician approval needed
        requires_approval = any(a.requires_physician_approval for a in workflow.actions)
        
        if requires_approval and not auto_approve:
            workflow.status = ExecutionStatus.REQUIRES_APPROVAL
            approval_request = self.approval_handler.request_approval(workflow)
            return workflow  # Pause here until approval
        
        # 4. Execute all actions
        print(f"\n{'='*60}")
        print(f"⚡ EXECUTING ACTIONS")
        print(f"{'='*60}\n")
        
        for action in workflow.actions:
            executed_action = await self.executor.execute_action(action)
            
            if executed_action.status == ExecutionStatus.FAILED:
                print(f"   ⚠️  Action failed but continuing with others")
        
        # 5. Send patient email
        patient_email = workflow_state.get("patient_email")
        if patient_email:
            print(f"\n📧 Sending patient email...")
            await asyncio.sleep(1)  # Simulate email sending
            workflow.patient_email_sent = True
            print(f"   ✅ Email sent to patient")
        
        # 6. Start continuous monitoring
        print(f"\n{'='*60}")
        print(f"📊 STARTING CONTINUOUS MONITORING")
        print(f"{'='*60}\n")
        
        self.monitor.register_workflow(workflow)
        asyncio.create_task(self.monitor.start_monitoring(workflow_id))
        
        # 7. Complete workflow
        workflow.completed_at = datetime.now()
        workflow.status = ExecutionStatus.COMPLETED
        
        print(f"\n{'='*60}")
        print(f"✅ WORKFLOW COMPLETED")
        print(f"{'='*60}")
        print(f"   Workflow ID: {workflow_id}")
        print(f"   Duration: {(workflow.completed_at - workflow.started_at).total_seconds():.2f}s")
        print(f"   Actions executed: {len([a for a in workflow.actions if a.status == ExecutionStatus.COMPLETED])}/{len(workflow.actions)}")
        print(f"   Monitoring: Active")
        print(f"{'='*60}\n")
        
        return workflow
    
    async def resume_after_approval(self, workflow_id: str, physician_id: str):
        """Resume workflow execution after physician approval"""
        
        if not self.approval_handler.approve_workflow(workflow_id, physician_id):
            print(f"❌ Cannot approve workflow {workflow_id} - not found")
            return
        
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return
        
        print(f"\n▶️  Resuming workflow {workflow_id} after approval\n")
        
        # Execute approved actions
        for action in workflow.actions:
            if action.status == ExecutionStatus.PENDING:
                await self.executor.execute_action(action)
        
        workflow.status = ExecutionStatus.COMPLETED
        workflow.completed_at = datetime.now()
        
        # Start monitoring
        self.monitor.register_workflow(workflow)
        asyncio.create_task(self.monitor.start_monitoring(workflow_id))
        
        print(f"✅ Workflow {workflow_id} completed and monitoring started")
    
    def get_physician_dashboard(self) -> Dict:
        """Generate data for physician dashboard"""
        
        active_workflows = [
            w for w in self.workflows.values()
            if w.status != ExecutionStatus.COMPLETED
        ]
        
        alerts = []
        for workflow in self.workflows.values():
            for alert in workflow.alerts:
                alerts.append({
                    **alert,
                    "workflow_id": workflow.workflow_id,
                    "patient_name": workflow.patient_name
                })
        
        pending_approvals = list(self.approval_handler.pending_approvals.values())
        
        return {
            "active_workflows": len(active_workflows),
            "pending_approvals": len(pending_approvals),
            "total_alerts": len(alerts),
            "high_priority_alerts": len([a for a in alerts if a.get("priority") == "high"]),
            "workflows": [
                {
                    "workflow_id": w.workflow_id,
                    "patient_name": w.patient_name,
                    "status": w.status.value,
                    "started_at": w.started_at.isoformat(),
                    "actions_completed": len([a for a in w.actions if a.status == ExecutionStatus.COMPLETED]),
                    "total_actions": len(w.actions),
                    "alerts": len(w.alerts)
                }
                for w in active_workflows
            ],
            "alerts": sorted(alerts, key=lambda x: x["timestamp"], reverse=True)[:10],
            "pending_approvals": [
                {
                    "workflow_id": w.workflow_id,
                    "patient_name": w.patient_name,
                    "actions_count": len(w.actions)
                }
                for w in pending_approvals
            ]
        }
