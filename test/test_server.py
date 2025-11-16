# test/test_server.py
import json
from fastapi_clerk_auth import ClerkHTTPBearer
import pytest
from fastapi.testclient import TestClient

# Import your FastAPI app directly from server.py
def test_consultation_summary_valid(client):
    """Test that a valid request yields a complete SSE event."""
    
    response = client.post("/api/consultation", json={
        "patient_name": "DARIN JESSIE WILLIAMS",
        "date_of_visit": "2025-11-15",
        "notes": "Chief Complaint: Headache\nHistory: Patient reports headache.\nPhysical Exam: Head - Tenderness\nAssessment: Tension headache (G44.2)\nPlan: Recommend acetaminophen as needed."
    })

    assert response.status_code == 200
    
    # Collect SSE chunks
    chunks = []
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8') if isinstance(line, bytes) else line
            chunks.append(line_str)
    
    # Verify we got a complete event
    full_text = '\n'.join(chunks)
    print(full_text)
    assert 'data:' in full_text
    assert '"type": "complete"' in full_text or '"type": "chunk"' in full_text

def test_consultation_summary_invalid_json(client):
    """Send malformed JSON to trigger JSONDecodeError path."""
    # Instead of sending JSON, send raw bad body
    response = client.post(
        "/api/consultation",
        data="{bad json",  # deliberately broken
        headers={"Content-Type": "application/json"}
    )
    chunks = list(response.iter_lines())
    assert any('"type": "error"' in chunk for chunk in chunks)


def test_consultation_summary_generic_error(client):
    """Force a generic error by omitting required fields."""
    response = client.post("/api/consultation", json={
        # Missing required fields
        "clinical_summary": {},
        "next_steps": {},
        "patient_email": {},
        "generation_timestamp": "2025-11-15T12:00:00Z"
    })
    chunks = list(response.iter_lines())
    assert any('"type": "error"' in chunk for chunk in chunks)
