# ============================================================================
# MONITORING AGENT - Continuous monitoring of patient health journey
# ============================================================================
from typing import Dict
from datetime import datetime
import asyncio
from execution_models.models import ExecutionStatus, WorkflowExecution
from langchain_openai import ChatOpenAI

class MonitoringAgent:
    """
    Continuously monitors patient workflows, tracks action completion,
    detects issues, and alerts physicians when needed.
    """
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.active_workflows: Dict[str, WorkflowExecution] = {}
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        
    def register_workflow(self, workflow: WorkflowExecution):
        """Register a workflow for monitoring"""
        self.active_workflows[workflow.workflow_id] = workflow
        print(f"\n📊 Monitoring Agent: Registered workflow {workflow.workflow_id}")
        
    async def monitor_lab_results(self, workflow_id: str, action_id: str):
        """Monitor for lab results and analyze when received"""
        print(f"   🔍 Monitoring lab results for action {action_id}")
        
        # Simulate waiting for lab results
        await asyncio.sleep(5)  # In production, this would poll lab API
        
        # Simulate receiving results
        lab_results = {
            "test": "Complete Blood Count",
            "hemoglobin": 12.5,
            "wbc": 7800,
            "platelets": 220000,
            "abnormal_flags": ["Hemoglobin slightly low"]
        }
        
        print(f"      📋 Lab results received")
        
        # Check if results need physician review
        if lab_results.get("abnormal_flags"):
            await self.alert_physician(
                workflow_id,
                "Lab Results Need Review",
                f"Abnormal findings: {', '.join(lab_results['abnormal_flags'])}"
            )
        
        return lab_results
    
    async def monitor_appointment_attendance(self, workflow_id: str, action_id: str, scheduled_date: datetime):
        """Monitor if patient attended scheduled appointment"""
        
        wait_time = (scheduled_date - datetime.now()).total_seconds()
        if wait_time > 0:
            await asyncio.sleep(min(wait_time + 3600, 10))  # Wait until 1hr after appointment (simulated)
        
        # Simulate checking attendance
        attended = True  # In production, check with scheduling system
        
        if not attended:
            await self.alert_physician(
                workflow_id,
                "Missed Appointment",
                f"Patient missed scheduled appointment on {scheduled_date}"
            )
        else:
            print(f"   ✅ Patient attended appointment")
        
        return attended
    
    async def monitor_medication_adherence(self, workflow_id: str, action_id: str):
        """Monitor if patient picked up and is taking medication"""
        
        # Check if prescription was picked up
        await asyncio.sleep(7)  # Wait ~1 week (simulated)
        
        picked_up = True  # In production, check with pharmacy API
        
        if not picked_up:
            await self.alert_physician(
                workflow_id,
                "Prescription Not Picked Up",
                "Patient has not picked up prescribed medication"
            )
            return False
        
        # After pickup, monitor adherence
        print(f"   💊 Monitoring medication adherence")
        return True
    
    async def alert_physician(self, workflow_id: str, alert_type: str, message: str):
        """Send alert to physician"""
        
        workflow = self.active_workflows.get(workflow_id)
        if workflow:
            alert = {
                "type": alert_type,
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "priority": "high" if "abnormal" in message.lower() or "missed" in message.lower() else "medium"
            }
            workflow.alerts.append(alert)
            
            print(f"\n   🚨 PHYSICIAN ALERT: {alert_type}")
            print(f"      {message}")
            print(f"      Priority: {alert['priority']}")
    
    async def start_monitoring(self, workflow_id: str):
        """Start continuous monitoring for a workflow"""
        
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return
        
        # Start monitoring tasks for each action
        for action in workflow.actions:
            if action.action_type == "lab" and action.status == ExecutionStatus.COMPLETED:
                task = asyncio.create_task(
                    self.monitor_lab_results(workflow_id, action.action_id)
                )
                self.monitoring_tasks[f"{workflow_id}:{action.action_id}:lab"] = task
            
            elif action.action_type == "follow-up" and action.status == ExecutionStatus.COMPLETED:
                scheduled = datetime.fromisoformat(action.result["date"])
                task = asyncio.create_task(
                    self.monitor_appointment_attendance(workflow_id, action.action_id, scheduled)
                )
                self.monitoring_tasks[f"{workflow_id}:{action.action_id}:appointment"] = task
            
            elif action.action_type == "medication" and action.status == ExecutionStatus.COMPLETED:
                task = asyncio.create_task(
                    self.monitor_medication_adherence(workflow_id, action.action_id)
                )
                self.monitoring_tasks[f"{workflow_id}:{action.action_id}:medication"] = task