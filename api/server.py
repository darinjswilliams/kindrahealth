import os
import json
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer, HTTPAuthorizationCredentials
from openai import OpenAI
from data_models.consultation import ConsultationSummaryResponse


app = FastAPI()

# Add CORS middleware (allows frontend to call backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Clerk authentication setup
clerk_config = ClerkConfig(jwks_url=os.getenv("CLERK_JWKS_URL"))
clerk_guard = ClerkHTTPBearer(clerk_config)

class Visit(BaseModel):
    patient_name: str
    date_of_visit: str
    notes: str

system_prompt = """
You are a medical documentation assistant. Always return valid JSON without markdown formatting.
"""

def create_structured_prompt(visit: Visit) -> str:

    """Create a structured prompt that instructs the LLM to return JSON"""
    return f"""You are a medical documentation assistant. Generate a comprehensive consultation summary based on the following information:

Patient Name: {visit.patient_name}
Visit Date: {visit.date_of_visit}

Consultation Notes:
{visit.notes}

Please generate a structured JSON response with the following EXACT format:

{{
  "clinical_summary": {{
    "patient_name": "{visit.patient_name}",
    "visit_date": "{visit.date_of_visit}",
    "chief_complaint": "Brief statement of primary complaint",
    "history_of_present_illness": "Detailed narrative of the patient's condition",
    "vital_signs": "Vital signs if mentioned (or null)",
    "physical_exam_findings": [
      {{
        "body_part": "Body part examined",
        "finding": "Examination finding"
      }}
    ],
    "assessments": [
      {{
        "diagnosis": "Clinical diagnosis",
        "icd_code": "ICD-10 code if applicable",
        "severity": "mild/moderate/severe"
      }}
    ],
    "additional_notes": "Any additional relevant notes"
  }},
  "next_steps": {{
    "actions": [
      {{
        "action_type": "diagnostic/treatment/referral/follow-up/education",
        "description": "Detailed description of the action",
        "priority": "high/medium/low",
        "timeline": "When this should be done"
      }}
    ],
    "follow_up_appointment": "Follow-up timeline",
    "red_flags": ["List of warning signs to watch for"]
  }},
  "patient_email": {{
    "greeting": "Dear {visit.patient_name},",
    "summary_of_findings": "Patient-friendly explanation of what was found",
    "treatment_plan": "Simple explanation of what we're doing",
    "patient_instructions": [
      {{
        "category": "medication/activity/self-care/warning",
        "instruction": "Clear, actionable instruction"
      }}
    ],
    "warning_signs": ["When to call immediately"],
    "next_steps_timeline": "What happens next and when",
    "closing": "Take care and feel free to reach out with any questions.",
    "physician_signature": "Your Healthcare Provider"
  }}
}}

IMPORTANT GUIDELINES:
1. Use clear, professional medical terminology in the clinical summary
2. Use simple, patient-friendly language in the patient email
3. Be specific and actionable in next steps
4. Include appropriate medical codes when applicable
5. Ensure all required fields are populated
6. Return ONLY valid JSON with no markdown formatting, no code blocks, no additional text
7. The response must be parseable by json.loads()

Generate the structured response now:"""

def user_prompt_for(visit: Visit) -> str:
    return f"""Create the summary, next steps and draft email for:
Patient Name: {visit.patient_name}
Date of Visit: {visit.date_of_visit}
Notes:
{visit.notes}"""

@app.post("/api/consultation")
async def consultation_summary(
    visit: Visit,
    creds: HTTPAuthorizationCredentials = Depends(clerk_guard),
):
    """
    Generate structured consultation summary with streaming support
    """
    try:
        user_id = creds.decoded["sub"]
        client = OpenAI()
        
        user_prompt = create_structured_prompt(visit)

        prompt = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        stream = client.chat.completions.create(
            model="gpt-5-nano",
            messages=prompt,
            stream=True,
        )

        async def event_stream():
            """Stream the JSON response as it's generated"""
            buffer = ""
            try:
                # Collect all chunks first
                for chunk in stream:
                    text = chunk.choices[0].delta.content
                    if text:
                        buffer += text
                        # Stream the raw content for real-time display
                        yield f"data: {json.dumps({'type': 'chunk', 'content': text})}\n\n"
                
                # After streaming completes, validate and parse the JSON
                try:
                    # Clean up the buffer (remove markdown code blocks if any)
                    clean_buffer = buffer.strip()
                    if clean_buffer.startswith("```json"):
                        clean_buffer = clean_buffer[7:]
                    if clean_buffer.startswith("```"):
                        clean_buffer = clean_buffer[3:]
                    if clean_buffer.endswith("```"):
                        clean_buffer = clean_buffer[:-3]
                    clean_buffer = clean_buffer.strip()
                    
                    # Parse the JSON
                    json_data = json.loads(clean_buffer)
                    
                    # Add metadata
                    json_data["generation_timestamp"] = datetime.utcnow().isoformat() + "Z"
                    json_data["model_version"] = "gpt-4o"
                    
                    # Validate with Pydantic
                    validated_response = ConsultationSummaryResponse(**json_data)
                    
                    # 🔥 FIX: Use model_dump(mode='json') to serialize dates properly
                    response_dict = validated_response.model_dump(mode='json')
                    
                    # Send the complete validated JSON
                    yield f"data: {json.dumps({'type': 'complete', 'data': response_dict})}\n\n"
                    
                except json.JSONDecodeError as e:
                    print(f"JSON Parse Error: {e}")
                    print(f"Buffer content: {buffer[:500]}...")
                    yield f"data: {json.dumps({'type': 'error', 'message': f'Failed to parse JSON: {str(e)}'})}\n\n"
                    
                except Exception as e:
                    print(f"Validation Error: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                    
            except Exception as e:
                print(f"Stream error: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except Exception as e:
        print(f"Error in consultation_summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    """Health check endpoint for AWS App Runner"""
    return {"status": "healthy"}

# Serve static files (our Next.js export) - MUST BE LAST!
static_path = Path("static")
if static_path.exists():
    # Serve index.html for the root path
    @app.get("/")
    async def serve_root():
        return FileResponse(static_path / "index.html")
    
    # Mount static files for all other routes
    app.mount("/", StaticFiles(directory="static", html=True), name="static")