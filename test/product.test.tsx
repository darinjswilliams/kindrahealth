import React from "react";
import { render, fireEvent, waitFor, screen } from "@testing-library/react";
import Product from "../pages/product";
import { fetchEventSource } from "@microsoft/fetch-event-source";
console.log("Product import:", Product);

const mockGetToken = jest.fn();

jest.mock("@microsoft/fetch-event-source", () => ({
  fetchEventSource: jest.fn(),
}));

jest.mock("@clerk/nextjs", () => ({
    UserButton: () => <div>UserButton</div>,
    Protect: ({ children }: any) => <div>{children}</div>,
    PricingTable: () => <div>PricingTable</div>,
    useAuth: () => ({ getToken: mockGetToken }),
  }));
  

  jest.mock("react-datepicker", () => {
    const ActualReactDatePicker = jest.requireActual("react-datepicker");
    return {
      __esModule: true,
      default: ({ onChange, selected, ...props }: any) => {
        return (
          <input
            type="date"
            data-testid="date-picker"
            value={selected ? selected.toISOString().split('T')[0] : ''}
            onChange={(e) => {
              if (onChange) {
                onChange(e.target.value ? new Date(e.target.value) : null, e);
              }
            }}
            // Don't spread props that aren't valid HTML attributes
          />
        );
      },
      registerLocale: jest.fn(),
    };
  });

describe("handleSubmit inside Product component", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetToken.mockResolvedValue("fake-jwt");
  });

  test("shows generating message when button is clicked", async () => {
    mockGetToken.mockResolvedValue("fake-jwt");
    
    // Mock fetchEventSource to delay so we can see the loading state
    (fetchEventSource as jest.Mock).mockImplementation(async (_url, opts) => {
      // Simulate a delay before returning data
      await new Promise(resolve => setTimeout(resolve, 100));
      
      opts.onmessage({ 
        data: JSON.stringify({ type: "chunk", content: "Hello" }) 
      });
    });
  
    render(<Product />);
    
    // Fill in form fields
    const patientInput = screen.getByPlaceholderText(/Enter patient's full name/i) || screen.getByLabelText(/Patient Name/i);
    const notesInput = screen.getByPlaceholderText(/notes/i) || screen.getByLabelText(/notes/i);
    
    fireEvent.change(patientInput, { target: { value: 'John Doe' } });
    fireEvent.change(notesInput, { target: { value: 'Test notes' } });
    
    const submitButton = screen.getByRole('button', { name: /generate summary/i });
    
    // Before click - button should show "Generate Summary"
    expect(submitButton).toHaveTextContent('Generate Summary');
    
    fireEvent.click(submitButton);
  
    // After click - button should show "Generating Summary..."
    await waitFor(() => {
      expect(screen.getByText('Generating Summary...')).toBeInTheDocument();
    });
    
    // Button should also be disabled
    expect(submitButton).toBeDisabled();
  });
  

  test("handles chunk and complete messages", async () => {
    mockGetToken.mockResolvedValue("fake-jwt");
    
    (fetchEventSource as jest.Mock).mockImplementation(async (_url, opts) => {
      // Simulate SSE messages
      opts.onmessage({ 
        data: JSON.stringify({ type: "chunk", content: "Hello " }) 
      });
      
      opts.onmessage({
        data: JSON.stringify({
          type: "complete",
          data: {
            clinical_summary: {
              patient_name: "John Doe",
              visit_date: "2025-11-15",
              chief_complaint: "Headache",
              history_of_present_illness: "Patient reports headache.",
              physical_exam_findings: [],
              assessments: [{
                diagnosis: "Test",
                icd_code: "Z00.0",
                severity: "mild"
              }],
              additional_notes: "None"
            },
            next_steps: { 
              actions: [{
                action_type: "follow-up",
                description: "Schedule follow-up",
                priority: "medium",
                timeline: "1 week"
              }],
              follow_up_appointment: "2025-11-20",
              red_flags: []
            },
            patient_email: {
              greeting: "Hi",
              summary_of_findings: "Summary",
              treatment_plan: "Plan",
              patient_instructions: [{
                category: "general",
                instruction: "Rest"
              }],
              warning_signs: [],
              next_steps_timeline: "Soon",
              closing: "Bye",
              physician_signature: "Dr. X",
            },
            generation_timestamp: "2025-11-15T12:00:00Z",
            model_version: "gpt-4o"
          },
        }),
      });
    });

    render(<Product />);
    
    // Fill in form fields
    const patientInput = screen.getByPlaceholderText(/Enter patient's full name/i) || screen.getByLabelText(/Patient Name/i);
    const notesInput = screen.getByPlaceholderText(/notes/i) || screen.getByLabelText(/notes/i);
    
    fireEvent.change(patientInput, { target: { value: 'John Doe' } });
    fireEvent.change(notesInput, { target: { value: 'Test notes' } });
    
    const submitButton = screen.getByRole('button', { name: /generate summary/i });
    fireEvent.click(submitButton);

    // Wait for structured output to appear
    await waitFor(() => {
      // Check if the patient name from the response is displayed
      expect(screen.getByText(/John Doe/i)).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  test("handles error message from backend", async () => {
    mockGetToken.mockResolvedValue("fake-jwt");
    
    (fetchEventSource as jest.Mock).mockImplementation(async (_url, opts) => {
      opts.onmessage({ 
        data: JSON.stringify({ 
          type: "error", 
          message: "Something went wrong" 
        }) 
      });
    });

    const alertSpy = jest.spyOn(window, "alert").mockImplementation(() => {});
    
    render(<Product />);
    
    // Fill in form fields
    const patientInput = screen.getByPlaceholderText(/Enter patient's full name/i) || screen.getByLabelText(/Patient Name/i);
    const notesInput = screen.getByPlaceholderText(/notes/i) || screen.getByLabelText(/Consultation Notes/i);
    
    fireEvent.change(patientInput, { target: { value: 'John Doe' } });
    fireEvent.change(notesInput, { target: { value: 'Test notes' } });
    
    const submitButton = screen.getByRole('button', { name: /generate summary/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(alertSpy).toHaveBeenCalledWith("Error: Something went wrong");
    });

    alertSpy.mockRestore();
  });
});
