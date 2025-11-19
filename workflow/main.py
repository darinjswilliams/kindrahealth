# ============================================================================
# EXAMPLE USAGE
# ============================================================================

async def main():
    """Example of complete workflow execution with monitoring"""
    
    # Import the workflow from the previous artifact
    from healthcare_workflow import run_consultation_workflow

    from langchain_openai import ChatOpenAI

    from execution_engine.healthcare_execution_engine import HealthcareExecutionEngine

    import json
    
    import asyncio
    
    # Initialize LLM and execution engine
    llm = ChatOpenAI(model="gpt-4o", temperature=0.2)
    engine = HealthcareExecutionEngine(llm)
    
    # 1. Run the agent workflow (from previous artifact)
    sample_notes = """
Patient presents with severe headaches, dizziness, and elevated blood pressure.
BP: 165/98, HR: 88, Temp: 98.6°F

Patient reports headaches started 1 week ago, progressively worsening.
Family history of hypertension.

Physical exam shows no neurological deficits.

Assessment: Essential hypertension, uncontrolled
Plan: Start antihypertensive, labs to check kidney function, follow-up in 2 weeks
"""
    
    print("Step 1: Running agent workflow to generate plan...")
    workflow_state = run_consultation_workflow(
        consultation_notes=sample_notes,
        patient_name="Jane Smith",
        patient_id="PT67890"
    )
    
    # 2. Execute the workflow with actions
    print("\nStep 2: Executing actions and starting monitoring...")
    execution = await engine.execute_workflow(workflow_state, auto_approve=True)
    
    # 3. Simulate monitoring (in production this runs continuously)
    print("\nStep 3: Monitoring active (simulating 10 seconds)...")
    await asyncio.sleep(10)
    
    # 4. Show physician dashboard
    print("\n" + "="*60)
    print("👨‍⚕️ PHYSICIAN DASHBOARD")
    print("="*60)
    dashboard = engine.get_physician_dashboard()
    print(json.dumps(dashboard, indent=2))


if __name__ == "__main__":
    import asyncio
    
    asyncio.run(main())