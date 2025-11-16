"use client"

import { useState, FormEvent } from 'react';
import { useAuth } from '@clerk/nextjs';
import DatePicker from 'react-datepicker';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { Protect, PricingTable, UserButton } from '@clerk/nextjs';
import { ConsultationSummaryResponseSchema, ConsultationSummaryResponse } from "../schemas";
import { formatClinicalSummary, formatNextSteps, formatPatientEmail } from "../utils/formatters";
import { FileText, Mail, ClipboardCheck, Calendar, User, Send, Copy, Download, Loader, CheckCircle } from 'lucide-react';
  

function ConsultationForm() {
    const { getToken } = useAuth();

    // Form state
    const [patientName, setPatientName] = useState('');
    const [visitDate, setVisitDate] = useState<Date | null>(new Date());
    const [notes, setNotes] = useState('');
    
    // Output state
    const [structuredOutput, setStructuredOutput] = useState<ConsultationSummaryResponse | null>(null);

    // Streaming state
    const [output, setOutput] = useState('');
    const [loading, setLoading] = useState(false);
    const [streamingBuffer, setStreamingBuffer] = useState('');
    const [copySuccess, setCopySuccess] = useState<string | null>(null);

    function handleCopy(text: string, type: string) {
        navigator.clipboard.writeText(text);
        setCopySuccess(type);
        setTimeout(() => setCopySuccess(null), 2000);
    }

    function handleDownload(text: string, filename: string) {
        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }

    async function handleSubmit(e: FormEvent) {
        e.preventDefault();
        setOutput('');
        setLoading(true);

        const jwt = await getToken();
        if (!jwt) {
            setOutput('Authentication required');
            setLoading(false);
            return;
        }

        const controller = new AbortController();
        let buffer = '';

        await fetchEventSource('/api/consultation', {
            signal: controller.signal,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${jwt}`,
            },
            body: JSON.stringify({
                patient_name: patientName,
                date_of_visit: visitDate?.toISOString().slice(0, 10),
                notes,
            }),
            onmessage(ev) {
            
                try {
                    const parsed = JSON.parse(ev.data);
                    
                    switch (parsed.type) {
                        case 'chunk':
                            // Real-time streaming text
                            buffer += parsed.content;
                            // Optional: Update UI with streaming text
                            // setStreamingText(buffer);
                            break;
                            
                        case 'complete':
                            // Final validated JSON received
                            console.log('Stream complete, received validated data');
                            const result = ConsultationSummaryResponseSchema.safeParse(parsed.data);
                            
                            if (result.success) {
                                setStructuredOutput(result.data);
                                setLoading(false);
                            } else {
                                console.error('Validation failed:', result.error);
                                alert('Failed to validate response');
                                setLoading(false);
                            }
                            break;
                            
                        case 'error':
                            // Handle errors from backend
                            console.error('Backend error:', parsed.message);
                            alert(`Error: ${parsed.message}`);
                            setLoading(false);
                            break;
                            
                        default:
                            console.warn('Unknown message type:', parsed.type);
                    }
                } catch (err) {
                    console.error('Failed to parse SSE message:', err);
                    console.log('Raw data:', ev.data);
                }
            },
            onclose() { 
                setLoading(false); 
            },
            onerror(err) {
                console.error('SSE error:', err);
                controller.abort();
                setLoading(false);
            },
        });
    }

    return (
        <div className="container mx-auto px-4 py-12 max-w-3xl">
            <h1 className="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-8">
                Consultation Notes
            </h1>

            <form onSubmit={handleSubmit} className="space-y-6 bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8">
                <div className="space-y-2">
                    <label htmlFor="patient" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        Patient Name
                    </label>
                    <input
                        id="patient"
                        type="text"
                        required
                        value={patientName}
                        onChange={(e) => setPatientName(e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                        placeholder="Enter patient's full name"
                    />
                </div>

                <div className="space-y-2">
                    <label htmlFor="date" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        Date of Visit
                    </label>
                    <DatePicker
                        id="date"
                        selected={visitDate}
                        onChange={(d: Date | null) => setVisitDate(d)}
                        dateFormat="yyyy-MM-dd"
                        placeholderText="Select date"
                        required
                        className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                    />
                </div>

                <div className="space-y-2">
                    <label htmlFor="notes" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        Consultation Notes
                    </label>
                    <textarea
                        id="notes"
                        required
                        rows={8}
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                        placeholder="Enter detailed consultation notes..."
                    />
                </div>

                <button 
                    type="submit" 
                    disabled={loading}
                    className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-200"
                >
                    {loading ? 'Generating Summary...' : 'Generate Summary'}
                </button>
            </form>

            {/* Streaming Preview (while generating) */}
            {loading && streamingBuffer && !structuredOutput && (
                    <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700 p-6 mb-6">
                        <div className="flex items-center gap-2 mb-4">
                            <Loader className="w-5 h-5 animate-spin text-blue-400" />
                            <h3 className="text-lg font-semibold text-white">Generating structured response...</h3>
                        </div>
                        <div className="bg-slate-900/50 rounded-lg p-4 max-h-96 overflow-auto">
                            <pre className="text-xs text-slate-300 whitespace-pre-wrap font-mono">
                                {streamingBuffer}
                            </pre>
                        </div>
                        <p className="text-sm text-slate-400 mt-4">
                            Please wait while the AI generates your clinical summary, next steps, and patient email...
                        </p>
                    </div>
                )}

                {/* Generated Results */}
                {structuredOutput && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Left Column - Doctor's Records */}
                        <div className="space-y-6">
                            {/* Clinical Summary */}
                            <div className="bg-gradient-to-br from-emerald-900/30 to-slate-800/50 backdrop-blur-sm rounded-2xl border border-emerald-700/50 overflow-hidden shadow-2xl">
                                <div className="bg-emerald-900/40 px-6 py-4 border-b border-emerald-700/50 flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <FileText className="w-5 h-5 text-emerald-400" />
                                        <h2 className="text-xl font-semibold text-white">Clinical Summary</h2>
                                    </div>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => handleCopy(formatClinicalSummary(structuredOutput.clinical_summary), 'clinical')}
                                            className="p-2 hover:bg-emerald-800/50 rounded-lg transition-colors relative"
                                            title="Copy to clipboard"
                                        >
                                            {copySuccess === 'clinical' ? (
                                                <CheckCircle className="w-4 h-4 text-emerald-300" />
                                            ) : (
                                                <Copy className="w-4 h-4 text-emerald-300" />
                                            )}
                                        </button>
                                        <button
                                            onClick={() => handleDownload(
                                                formatClinicalSummary(structuredOutput.clinical_summary),
                                                `clinical-summary-${patientName}-${visitDate?.toISOString().slice(0, 10)}.txt`
                                            )}
                                            className="p-2 hover:bg-emerald-800/50 rounded-lg transition-colors"
                                            title="Download"
                                        >
                                            <Download className="w-4 h-4 text-emerald-300" />
                                        </button>
                                    </div>
                                </div>
                                <div className="p-6 max-h-[600px] overflow-y-auto">
                                    <pre className="text-sm text-slate-200 whitespace-pre-wrap font-mono leading-relaxed">
                                        {formatClinicalSummary(structuredOutput.clinical_summary)}
                                    </pre>
                                </div>
                            </div>

                            {/* Next Steps */}
                            <div className="bg-gradient-to-br from-amber-900/30 to-slate-800/50 backdrop-blur-sm rounded-2xl border border-amber-700/50 overflow-hidden shadow-2xl">
                                <div className="bg-amber-900/40 px-6 py-4 border-b border-amber-700/50 flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <ClipboardCheck className="w-5 h-5 text-amber-400" />
                                        <h2 className="text-xl font-semibold text-white">Next Steps</h2>
                                    </div>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => handleCopy(formatNextSteps(structuredOutput.next_steps), 'nextsteps')}
                                            className="p-2 hover:bg-amber-800/50 rounded-lg transition-colors"
                                            title="Copy to clipboard"
                                        >
                                            {copySuccess === 'nextsteps' ? (
                                                <CheckCircle className="w-4 h-4 text-amber-300" />
                                            ) : (
                                                <Copy className="w-4 h-4 text-amber-300" />
                                            )}
                                        </button>
                                        <button
                                            onClick={() => handleDownload(
                                                formatNextSteps(structuredOutput.next_steps),
                                                `next-steps-${patientName}-${visitDate?.toISOString().slice(0, 10)}.txt`
                                            )}
                                            className="p-2 hover:bg-amber-800/50 rounded-lg transition-colors"
                                            title="Download"
                                        >
                                            <Download className="w-4 h-4 text-amber-300" />
                                        </button>
                                    </div>
                                </div>
                                <div className="p-6">
                                    <pre className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
                                        {formatNextSteps(structuredOutput.next_steps)}
                                    </pre>
                                </div>
                            </div>
                        </div>

                        {/* Right Column - Patient Email */}
                        <div className="lg:col-span-1">
                            <div className="bg-gradient-to-br from-blue-900/30 to-slate-800/50 backdrop-blur-sm rounded-2xl border border-blue-700/50 overflow-hidden shadow-2xl sticky top-6">
                                <div className="bg-blue-900/40 px-6 py-4 border-b border-blue-700/50 flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <Mail className="w-5 h-5 text-blue-400" />
                                        <h2 className="text-xl font-semibold text-white">Patient Follow-up Email</h2>
                                    </div>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => handleCopy(formatPatientEmail(structuredOutput.patient_email), 'email')}
                                            className="p-2 hover:bg-blue-800/50 rounded-lg transition-colors"
                                            title="Copy to clipboard"
                                        >
                                            {copySuccess === 'email' ? (
                                                <CheckCircle className="w-4 h-4 text-blue-300" />
                                            ) : (
                                                <Copy className="w-4 h-4 text-blue-300" />
                                            )}
                                        </button>
                                        <button
                                            onClick={() => handleDownload(
                                                formatPatientEmail(structuredOutput.patient_email),
                                                `patient-email-${patientName}-${visitDate?.toISOString().slice(0, 10)}.txt`
                                            )}
                                            className="p-2 hover:bg-blue-800/50 rounded-lg transition-colors"
                                            title="Download"
                                        >
                                            <Download className="w-4 h-4 text-blue-300" />
                                        </button>
                                    </div>
                                </div>
                                <div className="p-6 max-h-[600px] overflow-y-auto">
                                    <pre className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
                                        {formatPatientEmail(structuredOutput.patient_email)}
                                    </pre>
                                    <button className="w-full mt-6 px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600 text-white font-semibold rounded-lg transition-all transform hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2 shadow-lg shadow-blue-500/30">
                                        <Send className="w-4 h-4" />
                                        Send Email to Patient
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
        </div>
    );
}

export default function Product() {
    return (
        <main className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
            {/* User Menu in Top Right */}
            <div className="absolute top-4 right-4 z-50">
                <UserButton showName={true} />
            </div>

            {/* Subscription Protection */}
            <Protect
                plan="premium_subscription"
                fallback={
                    <div className="container mx-auto px-4 py-12">
                        <header className="text-center mb-12">
                            <h1 className="text-5xl font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent mb-4">
                                Healthcare Professional Plan
                            </h1>
                            <p className="text-slate-400 text-lg mb-8">
                                Streamline your patient consultations with AI-powered summaries
                            </p>
                        </header>
                        <div className="max-w-4xl mx-auto">
                            <PricingTable />
                        </div>
                    </div>
                }
            >
                <ConsultationForm />
            </Protect>
        </main>
    );
}

