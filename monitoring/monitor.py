"""
Complete Implementation of monitor_workflow and Related Functions
Background monitoring system for healthcare workflows
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from enum import Enum

from execution_models.models import (
    WorkflowExecution,
    ActionExecution,
    ExecutionStatus
)

logger = logging.getLogger(__name__)


# ============================================================================
# MONITORING CONFIGURATION
# ============================================================================

class MonitoringConfig:
    """Configuration for workflow monitoring"""
    
    # Polling intervals
    LAB_RESULTS_POLL_INTERVAL = 300  # 5 minutes
    APPOINTMENT_CHECK_INTERVAL = 3600  # 1 hour
    PRESCRIPTION_CHECK_INTERVAL = 1800  # 30 minutes
    
    # Timeouts
    LAB_RESULTS_TIMEOUT = timedelta(days=3)  # Alert if no results in 3 days
    PRESCRIPTION_PICKUP_TIMEOUT = timedelta(hours=24)  # Alert if not picked up in 24 hours
    APPOINTMENT_NO_SHOW_GRACE = timedelta(hours=1)  # Wait 1 hour after appointment
    
    # Maximum monitoring duration
    MAX_MONITORING_DURATION = timedelta(days=30)  # Stop monitoring after 30 days


# ============================================================================
# MAIN MONITORING FUNCTION
# ============================================================================

async def monitor_workflow(workflow_id: str, workflow_store: Dict[str, WorkflowExecution]):
    """
    Background task that monitors a workflow continuously
    
    This function:
    1. Monitors all actions in the workflow
    2. Checks for completion, results, and issues
    3. Alerts physicians when needed
    4. Updates workflow state
    5. Stops when workflow is complete or timeout reached
    
    Args:
        workflow_id: The workflow ID to monitor
        workflow_store: Dictionary storing all workflows
    """
    logger.info(f"🔍 Starting monitoring for workflow {workflow_id}")
    
    try:
        workflow = workflow_store.get(workflow_id)
        
        if not workflow:
            logger.error(f"❌ Workflow {workflow_id} not found in store")
            return
        
        # Calculate monitoring end time
        monitoring_start = datetime.now()
        monitoring_end = monitoring_start + MonitoringConfig.MAX_MONITORING_DURATION
        
        # Track what we're monitoring
        monitoring_tasks = []
        
        # Create monitoring tasks for each action
        for action in workflow.actions:
            if action.status == ExecutionStatus.COMPLETED:
                
                if action.action_type == "lab":
                    task = asyncio.create_task(
                        monitor_lab_results(workflow_id, action, workflow_store)
                    )
                    monitoring_tasks.append(task)
                    
                elif action.action_type == "imaging":
                    task = asyncio.create_task(
                        monitor_imaging_results(workflow_id, action, workflow_store)
                    )
                    monitoring_tasks.append(task)
                    
                elif action.action_type == "follow-up":
                    task = asyncio.create_task(
                        monitor_appointment_attendance(workflow_id, action, workflow_store)
                    )
                    monitoring_tasks.append(task)
                    
                elif action.action_type == "medication":
                    task = asyncio.create_task(
                        monitor_prescription_pickup(workflow_id, action, workflow_store)
                    )
                    monitoring_tasks.append(task)
                    
                elif action.action_type == "referral":
                    task = asyncio.create_task(
                        monitor_referral_completion(workflow_id, action, workflow_store)
                    )
                    monitoring_tasks.append(task)
        
        logger.info(f"📊 Created {len(monitoring_tasks)} monitoring tasks for workflow {workflow_id}")
        
        # Wait for all monitoring tasks to complete or timeout
        if monitoring_tasks:
            done, pending = await asyncio.wait(
                monitoring_tasks,
                timeout=(monitoring_end - monitoring_start).total_seconds(),
                return_when=asyncio.ALL_COMPLETED
            )
            
            # Cancel any pending tasks on timeout
            for task in pending:
                task.cancel()
                logger.warning(f"⏱️ Monitoring task cancelled due to timeout: {task}")
        
        logger.info(f"✅ Monitoring completed for workflow {workflow_id}")
        
    except Exception as e:
        logger.error(f"❌ Error monitoring workflow {workflow_id}: {str(e)}", exc_info=True)


# ============================================================================
# LAB RESULTS MONITORING
# ============================================================================

async def monitor_lab_results(
    workflow_id: str,
    action: ActionExecution,
    workflow_store: Dict[str, WorkflowExecution]
):
    """
    Monitor for lab results and alert physician when received
    
    Polls lab system API for results
    Analyzes results for abnormalities
    Alerts physician if action needed
    """
    logger.info(f"🧪 Monitoring lab results for action {action.action_id}")
    
    workflow = workflow_store.get(workflow_id)
    if not workflow:
        return
    
    order_id = action.result.get("order_id") if action.result else None
    if not order_id:
        logger.warning(f"⚠️ No order_id found for lab action {action.action_id}")
        return
    
    start_time = datetime.now()
    timeout = start_time + MonitoringConfig.LAB_RESULTS_TIMEOUT
    
    while datetime.now() < timeout:
        try:
            # Poll lab system for results
            results = await check_lab_system_for_results(order_id)
            
            if results and results.get("status") == "completed":
                logger.info(f"✅ Lab results received for action {action.action_id}")
                
                # Store results
                action.result["lab_results"] = results
                action.result["results_received_at"] = datetime.now().isoformat()
                
                # Analyze for abnormalities
                abnormalities = analyze_lab_results(results)
                
                if abnormalities:
                    # Alert physician
                    await alert_physician(
                        workflow,
                        alert_type="Abnormal Lab Results",
                        message=f"Lab order {order_id} has abnormal findings: {', '.join(abnormalities)}",
                        priority="high",
                        action_id=action.action_id,
                        details=results
                    )
                else:
                    logger.info(f"✓ Lab results normal for action {action.action_id}")
                
                return  # Results received, stop monitoring
            
            # Wait before next poll
            await asyncio.sleep(MonitoringConfig.LAB_RESULTS_POLL_INTERVAL)
            
        except Exception as e:
            logger.error(f"Error checking lab results: {str(e)}")
            await asyncio.sleep(MonitoringConfig.LAB_RESULTS_POLL_INTERVAL)
    
    # Timeout reached - no results
    logger.warning(f"⏱️ Timeout waiting for lab results: {action.action_id}")
    await alert_physician(
        workflow,
        alert_type="Lab Results Delayed",
        message=f"Lab order {order_id} has not returned results after {MonitoringConfig.LAB_RESULTS_TIMEOUT.days} days",
        priority="medium",
        action_id=action.action_id
    )


# ============================================================================
# IMAGING RESULTS MONITORING
# ============================================================================

async def monitor_imaging_results(
    workflow_id: str,
    action: ActionExecution,
    workflow_store: Dict[str, WorkflowExecution]
):
    """Monitor for imaging results (X-ray, MRI, CT scan, etc.)"""
    logger.info(f"📸 Monitoring imaging results for action {action.action_id}")
    
    workflow = workflow_store.get(workflow_id)
    if not workflow:
        return
    
    order_id = action.result.get("order_id") if action.result else None
    if not order_id:
        return
    
    start_time = datetime.now()
    timeout = start_time + timedelta(days=7)  # 7 days for imaging
    
    while datetime.now() < timeout:
        try:
            # Check PACS system for imaging results
            results = await check_imaging_system_for_results(order_id)
            
            if results and results.get("status") == "finalized":
                logger.info(f"✅ Imaging results available for action {action.action_id}")
                
                action.result["imaging_results"] = results
                action.result["results_received_at"] = datetime.now().isoformat()
                
                # Check for critical findings
                if results.get("critical_findings"):
                    await alert_physician(
                        workflow,
                        alert_type="Critical Imaging Findings",
                        message=f"Imaging order {order_id} has CRITICAL findings",
                        priority="high",
                        action_id=action.action_id,
                        details=results
                    )
                else:
                    await alert_physician(
                        workflow,
                        alert_type="Imaging Results Available",
                        message=f"Imaging results are ready for review",
                        priority="low",
                        action_id=action.action_id
                    )
                
                return
            
            await asyncio.sleep(3600)  # Check every hour
            
        except Exception as e:
            logger.error(f"Error checking imaging results: {str(e)}")
            await asyncio.sleep(3600)
    
    # Timeout
    await alert_physician(
        workflow,
        alert_type="Imaging Results Delayed",
        message=f"Imaging order {order_id} has not been completed",
        priority="medium",
        action_id=action.action_id
    )


# ============================================================================
# APPOINTMENT ATTENDANCE MONITORING
# ============================================================================

async def monitor_appointment_attendance(
    workflow_id: str,
    action: ActionExecution,
    workflow_store: Dict[str, WorkflowExecution]
):
    """Monitor if patient attended scheduled appointment"""
    logger.info(f"📅 Monitoring appointment attendance for action {action.action_id}")
    
    workflow = workflow_store.get(workflow_id)
    if not workflow:
        return
    
    appointment_id = action.result.get("appointment_id") if action.result else None
    scheduled_date_str = action.result.get("date") if action.result else None
    
    if not appointment_id or not scheduled_date_str:
        return
    
    try:
        scheduled_date = datetime.fromisoformat(scheduled_date_str)
    except ValueError:
        logger.error(f"Invalid appointment date format: {scheduled_date_str}")
        return
    
    # Wait until appointment time + grace period
    check_time = scheduled_date + MonitoringConfig.APPOINTMENT_NO_SHOW_GRACE
    wait_seconds = (check_time - datetime.now()).total_seconds()
    
    if wait_seconds > 0:
        logger.info(f"⏰ Waiting {wait_seconds/3600:.1f} hours until appointment check time")
        await asyncio.sleep(wait_seconds)
    
    # Check if patient attended
    try:
        attendance = await check_appointment_system(appointment_id)
        
        if attendance.get("attended"):
            logger.info(f"✅ Patient attended appointment {appointment_id}")
            action.result["attendance_confirmed"] = True
            action.result["attended_at"] = attendance.get("check_in_time")
        else:
            logger.warning(f"⚠️ Patient missed appointment {appointment_id}")
            action.result["attendance_confirmed"] = False
            
            await alert_physician(
                workflow,
                alert_type="Missed Appointment",
                message=f"Patient {workflow.patient_name} missed scheduled appointment on {scheduled_date_str}",
                priority="high",
                action_id=action.action_id,
                details={
                    "appointment_id": appointment_id,
                    "scheduled_date": scheduled_date_str,
                    "patient_id": workflow.patient_id
                }
            )
    
    except Exception as e:
        logger.error(f"Error checking appointment attendance: {str(e)}")


# ============================================================================
# PRESCRIPTION PICKUP MONITORING
# ============================================================================

async def monitor_prescription_pickup(
    workflow_id: str,
    action: ActionExecution,
    workflow_store: Dict[str, WorkflowExecution]
):
    """Monitor if patient picked up prescription"""
    logger.info(f"💊 Monitoring prescription pickup for action {action.action_id}")
    
    workflow = workflow_store.get(workflow_id)
    if not workflow:
        return
    
    prescription_id = action.result.get("prescription_id") if action.result else None
    if not prescription_id:
        return
    
    start_time = datetime.now()
    timeout = start_time + MonitoringConfig.PRESCRIPTION_CHECK_INTERVAL
    
    # Check periodically for pickup
    while datetime.now() < timeout:
        try:
            status = await check_pharmacy_system(prescription_id)
            
            if status.get("picked_up"):
                logger.info(f"✅ Prescription picked up: {prescription_id}")
                action.result["picked_up"] = True
                action.result["pickup_time"] = status.get("pickup_time")
                return
            
            await asyncio.sleep(1800)  # Check every 30 minutes
            
        except Exception as e:
            logger.error(f"Error checking prescription status: {str(e)}")
            await asyncio.sleep(1800)
    
    # Not picked up within timeout
    logger.warning(f"⚠️ Prescription not picked up: {prescription_id}")
    
    await alert_physician(
        workflow,
        alert_type="Prescription Not Picked Up",
        message=f"Patient has not picked up prescription {prescription_id} within 24 hours",
        priority="medium",
        action_id=action.action_id,
        details={
            "prescription_id": prescription_id,
            "medication": action.description,
            "pharmacy": action.result.get("pharmacy")
        }
    )


# ============================================================================
# REFERRAL COMPLETION MONITORING
# ============================================================================

async def monitor_referral_completion(
    workflow_id: str,
    action: ActionExecution,
    workflow_store: Dict[str, WorkflowExecution]
):
    """Monitor if patient completed specialist referral"""
    logger.info(f"👨‍⚕️ Monitoring referral completion for action {action.action_id}")
    
    workflow = workflow_store.get(workflow_id)
    if not workflow:
        return
    
    referral_id = action.result.get("referral_id") if action.result else None
    if not referral_id:
        return
    
    # Monitor for 30 days
    timeout = datetime.now() + timedelta(days=30)
    
    while datetime.now() < timeout:
        try:
            status = await check_referral_system(referral_id)
            
            if status.get("appointment_scheduled"):
                logger.info(f"✅ Specialist appointment scheduled for referral {referral_id}")
                action.result["appointment_scheduled"] = True
                action.result["specialist_appointment_date"] = status.get("appointment_date")
                return
            
            await asyncio.sleep(86400)  # Check daily
            
        except Exception as e:
            logger.error(f"Error checking referral status: {str(e)}")
            await asyncio.sleep(86400)
    
    # Timeout - referral not completed
    await alert_physician(
        workflow,
        alert_type="Referral Not Completed",
        message=f"Patient has not scheduled specialist appointment for referral {referral_id}",
        priority="medium",
        action_id=action.action_id
    )


# ============================================================================
# EXTERNAL SYSTEM INTEGRATION (Mock Functions)
# ============================================================================

async def check_lab_system_for_results(order_id: str) -> Optional[Dict]:
    """
    Check lab system for results
    In production: Integrate with LabCorp/Quest API
    """
    # Mock implementation - simulates API call
    await asyncio.sleep(0.1)
    
    # TODO: Replace with actual API call
    # response = await labcorp_api.get_results(order_id)
    
    # Simulate results
    import random
    if random.random() > 0.8:  # 20% chance results are ready
        return {
            "order_id": order_id,
            "status": "completed",
            "results": {
                "hemoglobin": 13.5,
                "wbc": 7800,
                "platelets": 250000
            },
            "abnormal_flags": []
        }
    return None


async def check_imaging_system_for_results(order_id: str) -> Optional[Dict]:
    """
    Check PACS system for imaging results
    In production: Integrate with radiology PACS API
    """
    await asyncio.sleep(0.1)
    
    # TODO: Replace with actual PACS API call
    
    return None


async def check_appointment_system(appointment_id: str) -> Dict:
    """
    Check if patient attended appointment
    In production: Integrate with scheduling system (Epic, Cerner, etc.)
    """
    await asyncio.sleep(0.1)
    
    # TODO: Replace with actual scheduling API
    # response = await epic_api.check_attendance(appointment_id)
    
    return {
        "attended": True,
        "check_in_time": datetime.now().isoformat()
    }


async def check_pharmacy_system(prescription_id: str) -> Dict:
    """
    Check if prescription was picked up
    In production: Integrate with pharmacy API (SureScripts, CVS, etc.)
    """
    await asyncio.sleep(0.1)
    
    # TODO: Replace with actual pharmacy API
    
    return {
        "picked_up": False,
        "status": "ready"
    }


async def check_referral_system(referral_id: str) -> Dict:
    """
    Check referral status
    In production: Integrate with referral management system
    """
    await asyncio.sleep(0.1)
    
    # TODO: Replace with actual referral tracking API
    
    return {
        "appointment_scheduled": False
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def analyze_lab_results(results: Dict) -> List[str]:
    """
    Analyze lab results for abnormalities
    
    In production: Use clinical decision support rules
    """
    abnormalities = []
    
    lab_values = results.get("results", {})
    
    # Check hemoglobin
    hgb = lab_values.get("hemoglobin")
    if hgb and hgb < 12.0:
        abnormalities.append("Low hemoglobin (anemia)")
    
    # Check WBC
    wbc = lab_values.get("wbc")
    if wbc and wbc > 11000:
        abnormalities.append("Elevated white blood cell count")
    
    # Check platelets
    platelets = lab_values.get("platelets")
    if platelets and platelets < 150000:
        abnormalities.append("Low platelet count")
    
    return abnormalities


async def alert_physician(
    workflow: WorkflowExecution,
    alert_type: str,
    message: str,
    priority: str = "medium",
    action_id: Optional[str] = None,
    details: Optional[Dict] = None
):
    """
    Send alert to physician
    
    In production: Send via multiple channels:
    - Push notification
    - Email
    - SMS (for critical alerts)
    - In-app notification
    """
    alert = {
        "type": alert_type,
        "message": message,
        "priority": priority,
        "timestamp": datetime.now().isoformat(),
        "action_id": action_id,
        "details": details or {}
    }
    
    workflow.alerts.append(alert)
    
    logger.info(f"🚨 ALERT [{priority.upper()}]: {alert_type} - {message}")
    
    # TODO: Send actual notifications
    # if priority == "high":
    #     await send_sms(physician_phone, message)
    #     await send_push_notification(physician_id, alert)
    # await send_email(physician_email, alert_type, message)
    
    return alert


# ============================================================================
# USAGE IN FASTAPI
# ============================================================================

# Add this to your FastAPI endpoints:

"""
from fastapi import BackgroundTasks

@app.post("/api/v1/consultations")
async def create_consultation(
    request: ConsultationCreateRequest,
    background_tasks: BackgroundTasks
):
    # Create workflow
    workflow = await create_workflow(request)
    
    # Start monitoring in background
    background_tasks.add_task(
        monitor_workflow,
        workflow.workflow_id,
        workflow_store
    )
    
    return {"workflow_id": workflow.workflow_id, "status": "processing"}
"""