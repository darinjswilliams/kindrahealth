from fastapi import FastAPI
from fastapi.security import HTTPBearer
from typing import Optional,Dict
import logging
from contextlib import asynccontextmanager

from langchain_openai import ChatOpenAI

from execution_models.models import WorkflowExecution

from executor_engine import HealthcareExecutionEngine

# ============================================================================
# CONFIGURATION
# ============================================================================

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

# Global state (in production, use Redis or database)
workflow_store: Dict[str, WorkflowExecution] = {}
execution_engine: Optional[HealthcareExecutionEngine] = None


# ============================================================================
# LIFESPAN MANAGEMENT
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown"""
    # Startup
    logger.info("🚀 Starting Healthcare Agent API...")
    
    # Initialize LLM
    global execution_engine
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.2,
        request_timeout=60
    )
    execution_engine = HealthcareExecutionEngine(llm)
    
    logger.info("✅ Healthcare Agent API ready")
    
    yield
    
    # Shutdown
    logger.info("🔴 Shutting down Healthcare Agent API...")




