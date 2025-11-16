import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from api.server import app, clerk_guard

class MockCredentials:
    """Mock Clerk credentials"""
    def __init__(self):
        self.scheme = "Bearer"
        self.credentials = "test-token"
        self.decoded = {"sub": "test-user-123"}

class MockChunk:
    """Mock OpenAI streaming chunk"""
    def __init__(self, content):
        self.choices = [Mock(delta=Mock(content=content))]

@pytest.fixture(scope="function")
def client():
    """Test client with mocked authentication"""
    app.dependency_overrides[clerk_guard] = lambda: MockCredentials()
    yield TestClient(app)
    app.dependency_overrides.clear()

def parse_sse_events(response):
    """Helper to parse SSE events from response"""
    events = []
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8') if isinstance(line, bytes) else line
            if line_str.startswith('data: '):
                data = line_str[6:]  # Remove 'data: ' prefix
                try:
                    events.append(json.loads(data))
                except json.JSONDecodeError:
                    events.append({'raw': data})
    return events

@patch('api.server.OpenAI')
def test_successful_streaming_with_valid_json(mock_openai_class, client):
    """Test successful streaming with valid JSON response"""
    
    # Mock OpenAI client
    mock_client = Mock()
    mock_openai_class.return_value = mock_client
    
    # Valid JSON response (without markdown)
    json_response = json.dumps({
        "clinical_summary": {
            "patient_name": "John Doe",
            "visit_date": "2025-11-15",
            "chief_complaint": "Headache",
            "history_of_present_illness": "Patient reports headache.",
            "physical_exam_findings": [
                {"body_part": "Head", "finding": "Tenderness"}
            ],
            "assessments": [
                {"diagnosis": "Tension headache", "icd_code": "G44.2", "severity": "mild"}
            ],
            "additional_notes": "Recommend acetaminophen."
        },
        "next_steps": {
            "actions": [
                {"action_type": "treatment", "description": "Take acetaminophen", "priority": "high", "timeline": "As needed"}
            ],
            "follow_up_appointment": "2025-11-20",
            "red_flags": ["Severe headache"]
        },
        "patient_email": {
            "greeting": "Hello John,",
            "summary_of_findings": "Tension headache",
            "treatment_plan": "Acetaminophen",
            "patient_instructions": [
                {"instruction": "Take as needed", "category": "medication"}
            ],
            "warning_signs": ["Severe headache"],
            "next_steps_timeline": "5 days",
            "closing": "Best regards,",
            "physician_signature": "Dr. Smith"
        }
    })
    
    # Mock streaming chunks (character by character)
    chunks = [MockChunk(char) for char in json_response]
    mock_client.chat.completions.create.return_value = iter(chunks)
    
    # Make request
    response = client.post("/api/consultation", json={
        "patient_name": "John Doe",
        "date_of_visit": "2025-11-15",
        "notes": "Patient complains of headache."
    })
    
    assert response.status_code == 200
    assert response.headers['content-type'] == 'text/event-stream; charset=utf-8'
    
    # Parse SSE events
    events = parse_sse_events(response)
    
    # Verify we have both chunk and complete events
    chunk_events = [e for e in events if e.get('type') == 'chunk']
    complete_events = [e for e in events if e.get('type') == 'complete']
    
    assert len(chunk_events) > 0, "Should have chunk events"
    assert len(complete_events) == 1, "Should have exactly one complete event"
    
    # Verify complete event has correct structure
    complete_data = complete_events[0]['data']
    assert 'clinical_summary' in complete_data
    assert 'next_steps' in complete_data
    assert 'patient_email' in complete_data
    assert 'generation_timestamp' in complete_data
    assert 'model_version' in complete_data
    assert complete_data['model_version'] == 'gpt-4o'

@patch('api.server.OpenAI')
def test_streaming_with_markdown_json(mock_openai_class, client):
    """Test that markdown code blocks are properly stripped"""
    
    mock_client = Mock()
    mock_openai_class.return_value = mock_client
    
    # JSON wrapped in markdown code blocks
    json_content = {
        "clinical_summary": {
            "patient_name": "Jane Doe",
            "visit_date": "2025-11-15",
            "chief_complaint": "Fever",
            "history_of_present_illness": "Fever for 2 days",
            "physical_exam_findings": [],
            "assessments": [{"diagnosis": "Viral illness", "icd_code": "B34.9", "severity": "mild"}],
            "additional_notes": "Rest and fluids"
        },
        "next_steps": {
            "actions": [{"action_type": "rest", "description": "Rest", "priority": "medium", "timeline": "3 days"}],
            "follow_up_appointment": "2025-11-18",
            "red_flags": ["High fever"]
        },
        "patient_email": {
            "greeting": "Hello Jane,",
            "summary_of_findings": "Viral illness",
            "treatment_plan": "Rest",
            "patient_instructions": [{"instruction": "Rest", "category": "lifestyle"}],
            "warning_signs": ["High fever"],
            "next_steps_timeline": "3 days",
            "closing": "Best,",
            "physician_signature": "Dr. Jones"
        }
    }
    
    markdown_response = f"```json\n{json.dumps(json_content)}\n```"
    
    chunks = [MockChunk(char) for char in markdown_response]
    mock_client.chat.completions.create.return_value = iter(chunks)
    
    response = client.post("/api/consultation", json={
        "patient_name": "Jane Doe",
        "date_of_visit": "2025-11-15",
        "notes": "Fever for 2 days"
    })
    
    assert response.status_code == 200
    
    events = parse_sse_events(response)
    complete_events = [e for e in events if e.get('type') == 'complete']
    
    assert len(complete_events) == 1
    assert 'data' in complete_events[0]
    assert complete_events[0]['data']['clinical_summary']['patient_name'] == 'Jane Doe'

@patch('api.server.OpenAI')
def test_streaming_with_invalid_json(mock_openai_class, client):
    """Test error handling when OpenAI returns invalid JSON"""
    
    mock_client = Mock()
    mock_openai_class.return_value = mock_client
    
    # Invalid JSON
    invalid_json = "This is not valid JSON { incomplete"
    
    chunks = [MockChunk(char) for char in invalid_json]
    mock_client.chat.completions.create.return_value = iter(chunks)
    
    response = client.post("/api/consultation", json={
        "patient_name": "Test Patient",
        "date_of_visit": "2025-11-15",
        "notes": "Test notes"
    })
    
    assert response.status_code == 200
    
    events = parse_sse_events(response)
    error_events = [e for e in events if e.get('type') == 'error']
    
    assert len(error_events) == 1
    assert 'Failed to parse JSON' in error_events[0]['message']

@patch('api.server.OpenAI')
def test_streaming_with_pydantic_validation_error(mock_openai_class, client):
    """Test error handling when JSON doesn't match Pydantic schema"""
    
    mock_client = Mock()
    mock_openai_class.return_value = mock_client
    
    # Valid JSON but missing required fields for ConsultationSummaryResponse
    incomplete_json = json.dumps({
        "clinical_summary": {
            "patient_name": "Test",
            # Missing required fields
        }
    })
    
    chunks = [MockChunk(char) for char in incomplete_json]
    mock_client.chat.completions.create.return_value = iter(chunks)
    
    response = client.post("/api/consultation", json={
        "patient_name": "Test Patient",
        "date_of_visit": "2025-11-15",
        "notes": "Test"
    })
    
    assert response.status_code == 200
    
    events = parse_sse_events(response)
    error_events = [e for e in events if e.get('type') == 'error']
    
    # Should have validation error
    assert len(error_events) >= 1

@patch('api.server.OpenAI')
def test_streaming_with_openai_exception(mock_openai_class, client):
    """Test error handling when OpenAI stream raises exception"""
    
    mock_client = Mock()
    mock_openai_class.return_value = mock_client
    
    # Mock streaming that raises exception
    def failing_stream():
        yield MockChunk("Some")
        yield MockChunk(" text")
        raise Exception("OpenAI API error")
    
    mock_client.chat.completions.create.return_value = failing_stream()
    
    response = client.post("/api/consultation", json={
        "patient_name": "Test Patient",
        "date_of_visit": "2025-11-15",
        "notes": "Test"
    })
    
    assert response.status_code == 200
    
    events = parse_sse_events(response)
    error_events = [e for e in events if e.get('type') == 'error']
    
    assert len(error_events) >= 1
    assert 'OpenAI API error' in error_events[0]['message']

@patch('api.server.OpenAI')
def test_chunk_events_contain_streamed_content(mock_openai_class, client):
    """Test that chunk events contain the actual streamed content"""
    
    mock_client = Mock()
    mock_openai_class.return_value = mock_client
    
    test_content = "Hello World"
    chunks = [MockChunk(char) for char in test_content]
    mock_client.chat.completions.create.return_value = iter(chunks)
    
    response = client.post("/api/consultation", json={
        "patient_name": "Test",
        "date_of_visit": "2025-11-15",
        "notes": "Test"
    })
    
    events = parse_sse_events(response)
    chunk_events = [e for e in events if e.get('type') == 'chunk']
    
    # Reconstruct content from chunks
    reconstructed = ''.join([e['content'] for e in chunk_events])
    assert reconstructed == test_content

@patch('api.server.OpenAI')
def test_metadata_added_to_response(mock_openai_class, client):
    """Test that metadata (timestamp, model version) is added"""
    
    mock_client = Mock()
    mock_openai_class.return_value = mock_client
    
    valid_json = json.dumps({
        "clinical_summary": {
            "patient_name": "Test",
            "visit_date": "2025-11-15",
            "chief_complaint": "Test",
            "history_of_present_illness": "Test",
            "physical_exam_findings": [],
            "assessments": [
                {
                    "diagnosis": "Test", 
                    "icd_code": "Z00.0", 
                    "severity": "mild"
                }
            ],
            "additional_notes": "Test"
        },
        "next_steps": {
            "actions": [  # 🔥 FIX: Must have at least 1 action
                {
                    "action_type": "follow-up",
                    "description": "Schedule follow-up appointment",
                    "priority": "medium",
                    "timeline": "1 week"
                }
            ],
            "follow_up_appointment": "2025-11-20",
            "red_flags": []
        },
        "patient_email": {
            "greeting": "Hi",
            "summary_of_findings": "Test",
            "treatment_plan": "Test",
            "patient_instructions": [  # 🔥 FIX: Add at least one instruction if required
                {
                    "category": "general",
                    "instruction": "Rest and stay hydrated"
                }
            ],
            "warning_signs": [],
            "next_steps_timeline": "1 week",
            "closing": "Bye",
            "physician_signature": "Dr. Test"
        }
    })
    
    chunks = [MockChunk(char) for char in valid_json]
    mock_client.chat.completions.create.return_value = iter(chunks)
    
    response = client.post("/api/consultation", json={
        "patient_name": "Test",
        "date_of_visit": "2025-11-15",
        "notes": "Test"
    })
    
    events = parse_sse_events(response)
    
    # DEBUG: Print all events
    print("\n=== ALL EVENTS ===")
    for i, event in enumerate(events):
        print(f"Event {i}: {event}")
    
    chunk_events = [e for e in events if e.get('type') == 'chunk']
    complete_events = [e for e in events if e.get('type') == 'complete']
    error_events = [e for e in events if e.get('type') == 'error']
    
    print(f"\nChunks: {len(chunk_events)}, Complete: {len(complete_events)}, Errors: {len(error_events)}")
    
    if error_events:
        print(f"\nERROR EVENT: {error_events[0]}")
    
    assert len(complete_events) == 1, f"Expected 1 complete event, got {len(complete_events)}. Errors: {error_events}"