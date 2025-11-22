"""
FastAPI Backend for Healthcare Agent System
Production-ready REST API exposing all agents and executors
"""

from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
import json
import uuid

from langchain_openai import ChatOpenAI

from monitoring.monitor import monitor_workflow

# Import agent system
from healthcare_agents import (
    OrchestratorAgent,    
)

from workflow_models.models import ConsultationInput
from workflow.healthcare_workflow import create_healthcare_workflow

from configuration import (
    lifespan, 
    logger, 
    security,
    execution_engine, 
    workflow_store
)


from execution_models import (
    WorkflowExecution,
    ExecutionStatus
)

from data_models import (
    ClinicalSummaryResponse,
    ConsultationCreateRequest,
    HealthCheckResponse,
    WorkflowResponse,
    WorkflowStatusEnum,
    ActionResponse,
    ApprovalRequest,
    DashboardResponse

)


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Healthcare Agent Orchestration API",
    description="Production REST API for autonomous healthcare workflow agents",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "https://yourdomain.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)


# ============================================================================
# AUTHENTICATION & AUTHORIZATION
# ============================================================================

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Verify JWT token and extract user information
    In production, integrate with your OAuth2/SSO provider
    """
    token = credentials.credentials
    
    # TODO: Replace with actual JWT verification
    # For now, simple validation
    if not token or len(token) < 10:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # In production, decode JWT and extract user_id
    # user_id = decode_jwt(token)
    user_id = "user_from_token"
    
    return user_id


async def verify_physician(user_id: str = Depends(verify_token)) -> str:
    """
    Verify user has physician role
    In production, check against role database
    """
    # TODO: Check user role in database
    # For now, assume all authenticated users are physicians
    return user_id


def audit_log(action: str, user_id: str, details: Dict[str, Any]):
    """
    Log action for HIPAA audit trail
    In production, write to secure audit database
    """
    logger.info(f"AUDIT: {action} | User: {user_id} | Details: {json.dumps(details)}")


# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================

@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def health_check():
    """Health check endpoint for load balancer"""
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="1.0.0",
        llm_available=execution_engine is not None
    )


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint"""
    return {
        "message": "Healthcare Agent Orchestration API",
        "version": "1.0.0",
        "docs": "/api/docs"
    }


# ============================================================================
# CONSULTATION WORKFLOW ENDPOINTS
# ============================================================================

@app.post(
    "/api/v1/consultations",
    response_model=WorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Consultations"]
)
async def create_consultation(
    request: ConsultationCreateRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(verify_physician)
):
    """
    Create a new consultation and trigger agent workflow
    
    This endpoint:
    1. Creates consultation record
    2. Triggers agent workflow (Clinical, Care Coordinator, Patient Comm)
    3. Executes approved actions
    4. Returns workflow status
    
    **Requires**: Physician authentication
    """
    try:
        # Audit log
        audit_log("create_consultation", user_id, {
            "patient_id": request.patient_id,
            "physician_id": request.physician_id
        })
        
        # Create consultation input
        consultation = ConsultationInput(
            patient_name=request.patient_name,
            patient_id=request.patient_id,
            date_of_visit=request.date_of_visit,
            consultation_notes=request.consultation_notes,
            physician_id=request.physician_id
        )
        
        # Initialize workflow state
        initial_state = {
            "consultation": consultation,
            "clinical_summary": None,
            "next_steps": None,
            "patient_email": None,
            "status": "initiated",
            "current_agent": "OrchestratorAgent",
            "errors": [],
            "physician_approval_required": False,
            "physician_approved": False,
            "messages": [],
            "executed_actions": []
        }
        
        # Run agent workflow
        logger.info(f"Starting workflow for patient {request.patient_id}")
        
        llm = ChatOpenAI(model="gpt-4o", temperature=0.2)
        workflow = create_healthcare_workflow(llm)
        final_state = workflow.invoke(initial_state)
        
        # Execute actions
        logger.info("Executing workflow actions")
        execution = await execution_engine.execute_workflow(
            final_state,
            auto_approve=request.auto_approve
        )
        
        # Store workflow
        workflow_store[execution.workflow_id] = execution
        
        # Build response
        response = build_workflow_response(execution, final_state)


         # ✅ Start monitoring (runs AFTER response is sent)
          # 🔥 START MONITORING IN BACKGROUND
        logger.info(f"🔍 Starting background monitoring for workflow {execution.workflow_id}")
        background_tasks.add_task(
            monitor_workflow,
            execution.workflow_id,
            workflow_store
        )

        
        logger.info(f"Workflow {execution.workflow_id} created successfully")
        
        return response
        
    except Exception as e:
        logger.error(f"Error creating consultation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create consultation: {str(e)}"
        )


@app.get(
    "/api/v1/consultations/{workflow_id}",
    response_model=WorkflowResponse,
    tags=["Consultations"]
)
async def get_consultation(
    workflow_id: str,
    user_id: str = Depends(verify_physician)
):
    """
    Get consultation workflow status and results
    
    **Requires**: Physician authentication
    """
    try:
        audit_log("get_consultation", user_id, {"workflow_id": workflow_id})
        
        workflow = workflow_store.get(workflow_id)
        
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        # In production, verify user has access to this patient
        # check_patient_access(user_id, workflow.patient_id)
        
        response = build_workflow_response(workflow)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving consultation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve consultation: {str(e)}"
        )


@app.get(
    "/api/v1/consultations",
    response_model=List[WorkflowResponse],
    tags=["Consultations"]
)
async def list_consultations(
    patient_id: Optional[str] = None,
    physician_id: Optional[str] = None,
    status: Optional[WorkflowStatusEnum] = None,
    limit: int = 50,
    offset: int = 0,
    user_id: str = Depends(verify_physician)
):
    """
    List consultations with optional filters
    
    **Query Parameters**:
    - patient_id: Filter by patient
    - physician_id: Filter by physician
    - status: Filter by workflow status
    - limit: Max results (default 50)
    - offset: Pagination offset (default 0)
    
    **Requires**: Physician authentication
    """
    try:
        audit_log("list_consultations", user_id, {
            "patient_id": patient_id,
            "physician_id": physician_id,
            "status": status
        })
        
        # Filter workflows
        workflows = list(workflow_store.values())
        
        if patient_id:
            workflows = [w for w in workflows if w.patient_id == patient_id]
        
        if physician_id:
            # In production, filter by physician_id from consultation
            pass
        
        if status:
            workflows = [w for w in workflows if w.status.value == status.value]
        
        # Sort by most recent
        workflows.sort(key=lambda w: w.started_at, reverse=True)
        
        # Pagination
        workflows = workflows[offset:offset + limit]
        
        # Build responses
        responses = [build_workflow_response(w) for w in workflows]
        
        return responses
        
    except Exception as e:
        logger.error(f"Error listing consultations: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list consultations: {str(e)}"
        )


# ============================================================================
# APPROVAL ENDPOINTS
# ============================================================================

@app.post(
    "/api/v1/approvals",
    status_code=status.HTTP_200_OK,
    tags=["Approvals"]
)
async def submit_approval(
    request: ApprovalRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(verify_physician)
):
    """
    Submit physician approval for pending workflow
    
    This endpoint:
    1. Approves or rejects pending workflow
    2. Optionally applies modifications
    3. Resumes workflow execution if approved
    
    **Requires**: Physician authentication
    """
    try:
        audit_log("submit_approval", user_id, {
            "workflow_id": request.workflow_id,
            "approved": request.approved,
            "physician_id": request.physician_id
        })
        
        workflow = workflow_store.get(request.workflow_id)
        
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {request.workflow_id} not found"
            )
        
        if workflow.status != ExecutionStatus.REQUIRES_APPROVAL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Workflow {request.workflow_id} does not require approval"
            )
        
        if request.approved:
            logger.info(f"Approving workflow {request.workflow_id}")
            
             # Apply any modifications if provided
            if request.modifications:
                logger.info(f"📝 Applying modifications to workflow {request.workflow_id}")
                apply_workflow_modifications(workflow, request.modifications)

                
            # Resume workflow execution
            await execution_engine.resume_after_approval(
                request.workflow_id,
                request.physician_id
            )

          # 🔥 START MONITORING IN BACKGROUND
            logger.info(f"🔍 Starting background monitoring for workflow {request.workflow_id}")
            background_tasks.add_task(
                monitor_workflow,
                request.workflow_id,
                workflow_store
            )
            
            return {
                "message": "Workflow approved and resumed",
                "workflow_id": request.workflow_id,
                "status": "monitoring_started",
                "monitoring_duration": "30 days"
            }
        else:
             logger.info(f"❌ Rejecting workflow {request.workflow_id}")
            
            # Mark as failed
             workflow.status = ExecutionStatus.FAILED
            
            # Log rejection reason if provided
             if request.notes:
                workflow.alerts.append({
                    "type": "Workflow Rejected",
                    "message": request.notes,
                    "timestamp": datetime.now().isoformat(),
                    "physician_id": request.physician_id
                })
            
             return {
                "message": "Workflow rejected",
                "workflow_id": request.workflow_id,
                "status": "failed",
                "reason": request.notes or "Rejected by physician"
             }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing approval: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process approval: {str(e)}"
        )


@app.get(
    "/api/v1/approvals/pending",
    tags=["Approvals"]
)
async def get_pending_approvals(
    user_id: str = Depends(verify_physician)
):
    """
    Get list of workflows pending physician approval
    
    **Requires**: Physician authentication
    """
    try:
        audit_log("get_pending_approvals", user_id, {})
        
        pending_workflows = [
            w for w in workflow_store.values()
            if w.status == ExecutionStatus.REQUIRES_APPROVAL
        ]
        
        # Sort by priority (workflows with high-priority actions first)
        pending_workflows.sort(
            key=lambda w: any(a.requires_physician_approval for a in w.actions),
            reverse=True
        )
        
        results = []
        for workflow in pending_workflows:
            results.append({
                "workflow_id": workflow.workflow_id,
                "patient_name": workflow.patient_name,
                "patient_id": workflow.patient_id,
                "started_at": workflow.started_at.isoformat(),
                "actions_requiring_approval": [
                    {
                        "action_id": a.action_id,
                        "action_type": a.action_type,
                        "description": a.description
                    }
                    for a in workflow.actions
                    if a.requires_physician_approval
                ]
            })
        
        return {
            "count": len(results),
            "pending_approvals": results
        }
        
    except Exception as e:
        logger.error(f"Error getting pending approvals: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pending approvals: {str(e)}"
        )


# ============================================================================
# DASHBOARD ENDPOINTS
# ============================================================================

@app.get(
    "/api/v1/dashboard",
    response_model=DashboardResponse,
    tags=["Dashboard"]
)
async def get_dashboard(
    user_id: str = Depends(verify_physician)
):
    """
    Get physician dashboard with active workflows, alerts, and approvals
    
    **Requires**: Physician authentication
    """
    try:
        audit_log("get_dashboard", user_id, {})
        
        dashboard = execution_engine.get_physician_dashboard()
        
        return DashboardResponse(**dashboard)
        
    except Exception as e:
        logger.error(f"Error getting dashboard: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard: {str(e)}"
        )


@app.get(
    "/api/v1/dashboard/alerts",
    tags=["Dashboard"]
)
async def get_alerts(
    priority: Optional[str] = None,
    limit: int = 20,
    user_id: str = Depends(verify_physician)
):
    """
    Get alerts for physician
    
    **Query Parameters**:
    - priority: Filter by priority (high, medium, low)
    - limit: Max results (default 20)
    
    **Requires**: Physician authentication
    """
    try:
        audit_log("get_alerts", user_id, {"priority": priority})
        
        # Collect all alerts from workflows
        all_alerts = []
        for workflow in workflow_store.values():
            for alert in workflow.alerts:
                all_alerts.append({
                    **alert,
                    "workflow_id": workflow.workflow_id,
                    "patient_name": workflow.patient_name,
                    "patient_id": workflow.patient_id
                })
        
        # Filter by priority if specified
        if priority:
            all_alerts = [a for a in all_alerts if a.get("priority") == priority]
        
        # Sort by timestamp (most recent first)
        all_alerts.sort(key=lambda a: a["timestamp"], reverse=True)
        
        # Limit results
        all_alerts = all_alerts[:limit]
        
        return {
            "count": len(all_alerts),
            "alerts": all_alerts
        }
        
    except Exception as e:
        logger.error(f"Error getting alerts: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alerts: {str(e)}"
        )


# ============================================================================
# ACTION ENDPOINTS
# ============================================================================

@app.get(
    "/api/v1/consultations/{workflow_id}/actions",
    response_model=List[ActionResponse],
    tags=["Actions"]
)
async def get_actions(
    workflow_id: str,
    user_id: str = Depends(verify_physician)
):
    """
    Get all actions for a specific workflow
    
    **Requires**: Physician authentication
    """
    try:
        audit_log("get_actions", user_id, {"workflow_id": workflow_id})
        
        workflow = workflow_store.get(workflow_id)
        
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        actions = [
            ActionResponse(
                action_id=a.action_id,
                action_type=a.action_type,
                description=a.description,
                status=a.status.value,
                executed_time=a.executed_time,
                result=a.result,
                error=a.error
            )
            for a in workflow.actions
        ]
        
        return actions
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting actions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get actions: {str(e)}"
        )


@app.post(
    "/api/v1/consultations/{workflow_id}/actions/{action_id}/retry",
    tags=["Actions"]
)
async def retry_action(
    workflow_id: str,
    action_id: str,
    user_id: str = Depends(verify_physician)
):
    """
    Retry a failed action
    
    **Requires**: Physician authentication
    """
    try:
        audit_log("retry_action", user_id, {
            "workflow_id": workflow_id,
            "action_id": action_id
        })
        
        workflow = workflow_store.get(workflow_id)
        
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        # Find action
        action = next((a for a in workflow.actions if a.action_id == action_id), None)
        
        if not action:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Action {action_id} not found"
            )
        
        if action.status != ExecutionStatus.FAILED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Action {action_id} is not in failed state"
            )
        
        # Retry action
        logger.info(f"Retrying action {action_id}")
        action.status = ExecutionStatus.PENDING
        action.error = None
        
        retried_action = await execution_engine.executor.execute_action(action)
        
        return {
            "message": "Action retried",
            "action_id": action_id,
            "new_status": retried_action.status.value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying action: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry action: {str(e)}"
        )


# ============================================================================
# STREAMING ENDPOINT (Real-time Updates)
# ============================================================================

@app.get(
    "/api/v1/consultations/{workflow_id}/stream",
    tags=["Consultations"]
)
async def stream_workflow(
    workflow_id: str,
    user_id: str = Depends(verify_physician)
):
    """
    Stream real-time updates for a workflow (Server-Sent Events)
    
    **Requires**: Physician authentication
    """
    
    async def event_generator():
        """Generate SSE events"""
        workflow = workflow_store.get(workflow_id)
        
        if not workflow:
            yield f"event: error\ndata: {json.dumps({'error': 'Workflow not found'})}\n\n"
            return
        
        # Send initial status
        yield f"event: status\ndata: {json.dumps({'status': workflow.status.value})}\n\n"
        
        # Monitor workflow and send updates
        last_status = workflow.status
        last_action_count = len(workflow.actions)
        
        for _ in range(60):  # Monitor for 60 seconds
            await asyncio.sleep(1)
            
            # Check for status changes
            if workflow.status != last_status:
                yield f"event: status\ndata: {json.dumps({'status': workflow.status.value})}\n\n"
                last_status = workflow.status
            
            # Check for new actions
            if len(workflow.actions) > last_action_count:
                new_actions = workflow.actions[last_action_count:]
                for action in new_actions:
                    yield f"event: action\ndata: {json.dumps({'action_id': action.action_id, 'status': action.status.value})}\n\n"
                last_action_count = len(workflow.actions)
            
            # Check for completion
            if workflow.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]:
                yield f"event: complete\ndata: {json.dumps({'status': workflow.status.value})}\n\n"
                break
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def build_workflow_response(
    workflow: WorkflowExecution,
    agent_state: Optional[Dict] = None
) -> WorkflowResponse:
    """Build workflow response from execution"""
    
    # Map execution status to response status
    status_map = {
        ExecutionStatus.PENDING: WorkflowStatusEnum.PENDING,
        ExecutionStatus.IN_PROGRESS: WorkflowStatusEnum.IN_PROGRESS,
        ExecutionStatus.REQUIRES_APPROVAL: WorkflowStatusEnum.AWAITING_APPROVAL,
        ExecutionStatus.COMPLETED: WorkflowStatusEnum.COMPLETED,
        ExecutionStatus.FAILED: WorkflowStatusEnum.FAILED
    }
    
    # Build clinical summary if available
    clinical_summary = None
    if agent_state and agent_state.get("clinical_summary"):
        cs = agent_state["clinical_summary"]
        clinical_summary = ClinicalSummaryResponse(
            patient_name=cs.patient_name,
            visit_date=cs.visit_date,
            chief_complaint=cs.chief_complaint,
            history_of_present_illness=cs.history_of_present_illness,
            vital_signs=cs.vital_signs,
            assessments=cs.assessments,
            icd_codes=cs.icd_codes
        )
    
    # Build actions
    actions = [
        ActionResponse(
            action_id=a.action_id,
            action_type=a.action_type,
            description=a.description,
            status=a.status.value,
            executed_time=a.executed_time,
            result=a.result,
            error=a.error
        )
        for a in workflow.actions
    ]
    
    return WorkflowResponse(
        workflow_id=workflow.workflow_id,
        patient_id=workflow.patient_id,
        patient_name=workflow.patient_name,
        consultation_id=workflow.consultation_id,
        status=status_map.get(workflow.status, WorkflowStatusEnum.PENDING),
        started_at=workflow.started_at,
        completed_at=workflow.completed_at,
        clinical_summary=clinical_summary,
        actions=actions,
        patient_email_sent=workflow.patient_email_sent,
        requires_approval=workflow.status == ExecutionStatus.REQUIRES_APPROVAL
    )

def apply_workflow_modifications(workflow: WorkflowExecution, modifications: Dict[str, Any]):
    """
    Apply physician modifications to workflow before resuming
    
    Args:
        workflow: The workflow to modify
        modifications: Dict of modifications to apply
        
    Example modifications:
    {
        "actions": {
            "ACT-001": {
                "description": "Modified lab order description",
                "priority": "high"
            }
        },
        "notes": "Physician notes about modifications"
    }
    """
    logger.info(f"Applying modifications to workflow {workflow.workflow_id}")
    
    # Modify specific actions if provided
    action_mods = modifications.get("actions", {})
    for action_id, mods in action_mods.items():
        action = next((a for a in workflow.actions if a.action_id == action_id), None)
        if action:
            if "description" in mods:
                action.description = mods["description"]
                logger.info(f"  Updated action {action_id} description")
            
            if "priority" in mods:
                # Update priority logic if needed
                logger.info(f"  Updated action {action_id} priority to {mods['priority']}")
    
    # Store modification notes
    if modifications.get("notes"):
        workflow.alerts.append({
            "type": "Workflow Modified",
            "message": modifications["notes"],
            "timestamp": datetime.now().isoformat()
        })

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return {
        "error": "Internal server error",
        "detail": str(exc) if app.debug else "An error occurred"
    }
    # Cleanup tasks here