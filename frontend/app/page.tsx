"use client";

import { useState } from "react";
import { UploadCloud, Activity, FileIcon, X, ShieldCheck, Terminal, AlertCircle, CheckCircle2, AlertTriangle, Scale, Receipt, ChevronRight, ChevronLeft, Code } from "lucide-react";

// --- THE FIX: Map the UI required documents directly to the JSON policy ---
const REQUIREMENT_MAP: Record<string, string[]> = {
  CONSULTATION: ["PRESCRIPTION", "HOSPITAL_BILL"],
  DIAGNOSTIC: ["PRESCRIPTION", "LAB_REPORT", "HOSPITAL_BILL"],
  PHARMACY: ["PRESCRIPTION", "PHARMACY_BILL"],
  DENTAL: ["HOSPITAL_BILL"],
  VISION: ["PRESCRIPTION", "HOSPITAL_BILL"],
  ALTERNATIVE_MEDICINE: ["PRESCRIPTION", "HOSPITAL_BILL"],
};

const DOC_LABELS: Record<string, string> = {
  PRESCRIPTION: "Doctor's Prescription",
  HOSPITAL_BILL: "Hospital/Clinic Invoice",
  LAB_REPORT: "Diagnostic Lab Report",
  PHARMACY_BILL: "Pharmacy Receipt"
};

export default function ClaimsDashboard() {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    memberId: "",
    policyId: "PLUM_GHI_2024",
    claimCategory: "CONSULTATION",
    treatmentDate: "",
    claimedAmount: ""
  });
  
  // Dynamic Files State
  const [requiredFiles, setRequiredFiles] = useState<Record<string, File>>({});
  const [otherFiles, setOtherFiles] = useState<File[]>([]);
  
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDevMode, setIsDevMode] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [step1Error, setStep1Error] = useState<string | null>(null);

  const todayDate = new Date().toISOString().split('T')[0];
  const activeRequiredDocs = REQUIREMENT_MAP[formData.claimCategory] || ["HOSPITAL_BILL"];

  const handleTextChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    if (e.target.name === "claimedAmount" && Number(e.target.value) < 0) return;
    
    // Clear previously uploaded files if they change the category to avoid mismatched data
    if (e.target.name === "claimCategory") setRequiredFiles({});
    
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setStep1Error(null);
  };

  const nextStep = () => setStep(prev => prev + 1);
  const prevStep = () => setStep(prev => prev - 1);
  
  const resetWizard = () => {
    setStep(1);
    setRequiredFiles({});
    setOtherFiles([]);
    setResult(null);
    setError(null);
    setStep1Error(null);
  };

  const handleRequiredFileChange = (docType: string, e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setRequiredFiles({ ...requiredFiles, [docType]: e.target.files[0] });
      setError(null);
    }
  };

  const handleOtherFilesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) setOtherFiles(prev => [...prev, ...Array.from(e.target.files!)]);
  };

  const removeOtherFile = (index: number) => {
    setOtherFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleVerifyPolicy = async () => {
    setIsVerifying(true);
    setStep1Error(null);
    
    try {
      const targetUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const response = await fetch(`${targetUrl}/api/v1/verify-policy`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          member_id: formData.memberId,
          policy_id: formData.policyId
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        if (Array.isArray(errorData.detail)) {
            const msgs = errorData.detail.map((err: any) => `${err.loc[err.loc.length - 1]}: ${err.msg}`);
            throw new Error(msgs.join(" | "));
        }
        throw new Error(errorData.detail || "Policy verification failed.");
      }
      setStep(2);
    } catch (err: any) {
      setStep1Error(err.message);
    } finally {
      setIsVerifying(false);
    }
  };

  const handleProcessClaim = async () => {
    setIsProcessing(true);
    setResult(null);
    setError(null);

    const payload = new FormData();
    payload.append("member_id", formData.memberId);
    payload.append("policy_id", formData.policyId);
    payload.append("claim_category", formData.claimCategory);
    payload.append("treatment_date", formData.treatmentDate);
    payload.append("claimed_amount", formData.claimedAmount);
    
    // Append all required and optional files under the generic "files" key
    Object.values(requiredFiles).forEach(file => payload.append("files", file));
    otherFiles.forEach(file => payload.append("files", file));

    try {
      const targetUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const response = await fetch(`${targetUrl}/api/v1/process-claim`, {
        method: "POST",
        body: payload,
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        if (Array.isArray(errorData.detail)) {
            const msgs = errorData.detail.map((err: any) => `${err.loc[err.loc.length - 1]}: ${err.msg}`);
            throw new Error(`Data Validation Failed -> ${msgs.join(" | ")}`);
        }
        throw new Error(errorData.detail || "Server rejected the request.");
      }
      
      const data = await response.json();
      
      if (data.stop_pipeline && data.validation_errors?.length > 0) {
        const errorText = data.validation_errors.join(" ").toUpperCase();
        
        // Smart Routing: Kick user back to the exact step of the failed document
        let routed = false;
        for (let i = 0; i < activeRequiredDocs.length; i++) {
            if (errorText.includes(activeRequiredDocs[i])) {
                setError(data.validation_errors.join(" | "));
                setStep(i + 2); 
                routed = true;
                break;
            }
        }
        if (!routed) {
            setResult(data);
            setStep(activeRequiredDocs.length + 3);
        }
      } else {
        setResult(data);
        setStep(activeRequiredDocs.length + 3);
      }
    } catch (err: any) {
      setError(err.message || "Failed to connect to the engine.");
    } finally {
      setIsProcessing(false);
    }
  };

  // Dynamic Wizard Step Renderers
  const renderDocumentStep = (docType: string, stepIndex: number) => {
    const file = requiredFiles[docType];
    const label = DOC_LABELS[docType] || docType.replace('_', ' ');

    return (
      <div className="space-y-4 animate-in fade-in slide-in-from-right-4 duration-300" key={docType}>
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-800">Upload {label}</h3>
            <p className="text-xs text-slate-500 mt-1">Ensure text is legible. Blurry images will be rejected by the AI.</p>
          </div>
        </div>

        {error && (
          <div className="bg-rose-50 border border-rose-200 text-rose-700 p-3 rounded-lg text-sm flex items-start gap-2 animate-bounce">
            <AlertCircle size={16} className="mt-0.5 flex-shrink-0" />
            <span><strong>AI Rejection:</strong> {error}</span>
          </div>
        )}

        <div className={`border-2 border-dashed rounded-xl p-8 transition-all relative ${error ? 'border-rose-400 bg-rose-50/30' : 'border-slate-300 hover:bg-slate-50 hover:border-indigo-400'}`}>
          <input type="file" accept=".jpg,.jpeg,.png,.pdf" className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10" onChange={(e) => handleRequiredFileChange(docType, e)} />
          <div className="flex flex-col items-center pointer-events-none text-center">
            <div className={`p-3 rounded-full mb-3 ${file ? 'bg-emerald-100 text-emerald-600' : 'bg-indigo-50 text-indigo-500'}`}>
              {file ? <CheckCircle2 size={28}/> : <UploadCloud size={28} />}
            </div>
            <span className="text-sm font-semibold text-slate-700">
              {file ? "Document Attached" : `Tap or Drag to Upload ${label}`}
            </span>
          </div>
        </div>
        
        {file && (
          <div className="flex items-center justify-between bg-emerald-50 border border-emerald-200 px-3 py-2 rounded-lg text-sm animate-in fade-in">
            <div className="flex items-center gap-2 overflow-hidden text-emerald-800 font-medium">
              <FileIcon size={16} /> <span className="truncate">{file.name}</span>
            </div>
          </div>
        )}
      </div>
    );
  };

  const isResultsStep = step === activeRequiredDocs.length + 3;
  const isOptionalDocsStep = step === activeRequiredDocs.length + 2;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans selection:bg-indigo-100 selection:text-indigo-900">
      <nav className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between sticky top-0 z-10 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="bg-indigo-600 p-2 rounded-lg">
            <ShieldCheck className="text-white" size={24} />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900">Plum Claims Portal</h1>
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Automated Processing</p>
          </div>
        </div>
        
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2 bg-slate-100 px-3 py-1.5 rounded-full border border-slate-200">
            <Code size={14} className={isDevMode ? "text-indigo-600" : "text-slate-400"} />
            <span className="text-xs font-semibold text-slate-600">Dev Mode</span>
            <button onClick={() => setIsDevMode(!isDevMode)} className={`w-8 h-4 rounded-full transition-colors relative ${isDevMode ? "bg-indigo-600" : "bg-slate-300"}`}>
              <div className={`w-3 h-3 bg-white rounded-full absolute top-0.5 transition-transform ${isDevMode ? "translate-x-4.5 right-0.5" : "translate-x-0.5 left-0"}`}></div>
            </button>
          </div>
          <span className="flex items-center gap-2 text-sm font-medium text-slate-600">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span> System Online
          </span>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* LEFT WIZARD PANEL */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full min-h-[600px]">
            
            {/* Dynamic Breadcrumbs */}
            <div className="p-6 border-b border-slate-100 bg-slate-50/50">
              <h2 className="text-lg font-semibold text-slate-800">Claim Submission</h2>
              <div className="flex flex-wrap items-center gap-2 mt-2 text-xs font-medium text-slate-400">
                <span className={step >= 1 ? "text-indigo-600 font-bold" : ""}>1. Policy</span>
                {activeRequiredDocs.map((doc, idx) => (
                   <span key={doc} className={step >= 2 + idx ? "text-indigo-600 font-bold flex items-center" : "flex items-center"}>
                     <ChevronRight size={12} className="mx-1 opacity-50"/>
                     {idx + 2}. {doc.split('_')[0]}
                   </span>
                ))}
                <span className={step >= activeRequiredDocs.length + 2 ? "text-indigo-600 font-bold flex items-center" : "flex items-center"}>
                   <ChevronRight size={12} className="mx-1 opacity-50"/>
                   {activeRequiredDocs.length + 2}. Extras
                </span>
              </div>
            </div>
            
            <div className="p-6 flex-grow flex flex-col justify-between">
              
              {/* STEP 1: Policy Info */}
              {step === 1 && (
                <div className="space-y-5 animate-in fade-in slide-in-from-right-4 duration-300">
                  <div className="bg-blue-50 text-blue-800 p-4 rounded-xl border border-blue-100 text-sm mb-4">
                    <strong>Welcome.</strong> Please verify your identity and policy details to begin the automated claim process.
                  </div>

                  {step1Error && (
                    <div className="bg-rose-50 text-rose-700 p-3 rounded-lg text-sm flex items-start gap-2 border border-rose-200">
                      <AlertCircle size={16} className="mt-0.5 flex-shrink-0" />
                      <span>{step1Error}</span>
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">Member ID</label>
                      <input type="text" name="memberId" value={formData.memberId} onChange={handleTextChange} placeholder="e.g. EMP001" className="w-full border border-slate-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 outline-none transition-all" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">Policy ID</label>
                      <input type="text" name="policyId" value={formData.policyId} onChange={handleTextChange} className="w-full border border-slate-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 outline-none transition-all bg-slate-50" />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Type of Claim</label>
                    <select name="claimCategory" value={formData.claimCategory} onChange={handleTextChange} className="w-full border border-slate-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 outline-none bg-white">
                      <option value="CONSULTATION">Doctor Consultation</option>
                      <option value="DIAGNOSTIC">Diagnostic / Lab Test</option>
                      <option value="PHARMACY">Pharmacy / Medicine</option>
                      <option value="DENTAL">Dental Treatment</option>
                      <option value="VISION">Vision / Eye Care</option>
                      <option value="ALTERNATIVE_MEDICINE">Alternative Medicine (AYUSH)</option>
                    </select>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">Date of Service</label>
                      <input type="date" name="treatmentDate" value={formData.treatmentDate} onChange={handleTextChange} max={todayDate} className="w-full border border-slate-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 outline-none" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">Total Claimed (₹)</label>
                      <input type="number" name="claimedAmount" value={formData.claimedAmount} onChange={handleTextChange} min="0" placeholder="0.00" className="w-full border border-slate-300 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-indigo-500 outline-none" />
                    </div>
                  </div>
                </div>
              )}

              {/* DYNAMIC REQUIRED DOCS STEPS (Steps 2 to N) */}
              {step > 1 && step <= activeRequiredDocs.length + 1 && renderDocumentStep(activeRequiredDocs[step - 2], step)}

              {/* OPTIONAL DOCS STEP */}
              {isOptionalDocsStep && (
                <div className="space-y-4 animate-in fade-in slide-in-from-right-4 duration-300">
                  <div>
                    <h3 className="text-sm font-bold text-slate-800">Additional Documents (Optional)</h3>
                    <p className="text-xs text-slate-500 mt-1">Upload lab reports, discharge summaries, or pre-authorization letters.</p>
                  </div>

                  <div className="border-2 border-dashed border-slate-300 rounded-xl p-6 transition-all hover:bg-slate-50 hover:border-indigo-400 relative">
                    <input type="file" multiple accept=".jpg,.jpeg,.png,.pdf" className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10" onChange={handleOtherFilesChange} />
                    <div className="flex flex-col items-center pointer-events-none">
                      <UploadCloud size={24} className="text-indigo-400 mb-2" />
                      <span className="text-sm font-semibold text-slate-600">Add Optional Files</span>
                    </div>
                  </div>

                  {otherFiles.length > 0 && (
                    <div className="space-y-2 mt-4 max-h-[150px] overflow-y-auto custom-scrollbar pr-2">
                      {otherFiles.map((f, idx) => (
                        <div key={idx} className="flex items-center justify-between bg-slate-50 border border-slate-200 px-3 py-2 rounded-lg text-sm">
                          <div className="flex items-center gap-2 overflow-hidden text-slate-700">
                            <FileIcon size={14} className="text-slate-400"/> <span className="truncate">{f.name}</span>
                          </div>
                          <button onClick={() => removeOtherFile(idx)} className="text-slate-400 hover:text-rose-500 z-20 relative p-1"><X size={14}/></button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* SUCCESS RESULT SCREEN */}
              {isResultsStep && (
                <div className="flex flex-col items-center justify-center h-full space-y-4 text-center animate-in zoom-in duration-500">
                  <div className="bg-emerald-100 p-4 rounded-full">
                    <CheckCircle2 size={48} className="text-emerald-600" />
                  </div>
                  <h3 className="text-xl font-bold text-slate-800">Claim Processed</h3>
                  <p className="text-sm text-slate-500">The Neuro-Symbolic AI has completed adjudication. See your results on the dashboard.</p>
                </div>
              )}

              {/* NAVIGATION CONTROLS */}
              <div className="mt-8 pt-6 border-t border-slate-100 flex gap-3">
                {step > 1 && !isResultsStep && (
                  <button onClick={prevStep} disabled={isProcessing || isVerifying} className="px-4 py-2.5 rounded-xl font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 transition-all flex items-center justify-center">
                    <ChevronLeft size={18} />
                  </button>
                )}
                
                {step === 1 && (
                  <button onClick={handleVerifyPolicy} disabled={isVerifying || !formData.memberId || !formData.treatmentDate || !formData.claimedAmount || !formData.policyId} className="flex-1 py-2.5 rounded-xl font-semibold bg-indigo-600 text-white hover:bg-indigo-700 transition-all disabled:opacity-50 flex items-center justify-center gap-2">
                    {isVerifying ? <><Activity size={16} className="animate-spin"/> Verifying...</> : "Verify Policy & Continue"}
                  </button>
                )}

                {step > 1 && step <= activeRequiredDocs.length + 1 && (
                  <button onClick={nextStep} disabled={!requiredFiles[activeRequiredDocs[step - 2]]} className="flex-1 py-2.5 rounded-xl font-semibold bg-indigo-600 text-white hover:bg-indigo-700 transition-all disabled:opacity-50">
                    Upload {DOC_LABELS[activeRequiredDocs[step - 2]] || activeRequiredDocs[step - 2]}
                  </button>
                )}

                {isOptionalDocsStep && (
                  <button onClick={handleProcessClaim} disabled={isProcessing} className="flex-1 py-2.5 rounded-xl font-bold text-white bg-emerald-600 hover:bg-emerald-700 transition-all shadow-lg shadow-emerald-200 flex items-center justify-center gap-2">
                    {isProcessing ? <><Activity className="animate-spin" size={18} /> Executing...</> : "Submit Claim"}
                  </button>
                )}

                {isResultsStep && (
                  <button onClick={resetWizard} className="flex-1 py-2.5 rounded-xl font-semibold border border-slate-300 text-slate-700 hover:bg-slate-50 transition-all">
                    Start New Claim
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT DASHBOARD PANEL */}
        <div className="lg:col-span-7 flex flex-col">
          
          {!isProcessing && !result && error && !isOptionalDocsStep && step > 1 && (
            <div className="bg-rose-50 rounded-2xl border border-rose-200 flex flex-col items-center justify-center h-full min-h-[500px] text-rose-600 p-8 text-center animate-in fade-in">
              <AlertCircle size={48} className="mb-4 opacity-80" />
              <h3 className="text-lg font-semibold text-rose-900 mb-2">Pipeline Execution Failed</h3>
              <p className="text-sm text-rose-700 max-w-md">{error}</p>
            </div>
          )}

          {!isProcessing && !result && !error && (
            <div className="bg-slate-100/50 rounded-2xl border border-slate-200 border-dashed flex flex-col items-center justify-center h-full min-h-[500px] text-slate-400">
              <Activity size={48} className="mb-4 text-slate-300 stroke-[1.5]" />
              <h3 className="text-lg font-medium text-slate-600 mb-1">Awaiting Submission</h3>
              <p className="text-sm max-w-sm text-center">Complete the ingestion wizard. Your descriptive claim statistics and metrics will appear here.</p>
            </div>
          )}

          {isProcessing && (
            <div className="bg-white rounded-2xl shadow-lg shadow-slate-200/50 border border-slate-100 flex flex-col items-center justify-center h-full min-h-[500px] space-y-6">
              <div className="relative">
                <div className="absolute inset-0 bg-indigo-200 rounded-full animate-ping opacity-75"></div>
                <div className="relative bg-indigo-600 p-4 rounded-full text-white shadow-xl shadow-indigo-200">
                  <Activity size={32} className="animate-spin" />
                </div>
              </div>
              <div className="text-center">
                <h3 className="text-xl font-bold text-slate-800">Evaluating Claim...</h3>
                <div className="mt-4 space-y-2 text-sm font-medium text-slate-500">
                  <p className="flex items-center justify-center gap-2 animate-pulse"><CheckCircle2 size={16} className="text-emerald-500"/> Checking Policy & Fraud Velocity</p>
                  <p className="flex items-center justify-center gap-2 animate-pulse delay-75"><Activity size={16} className="text-indigo-500"/> Extracting Semantics via Gemini Vision</p>
                  <p className="flex items-center justify-center gap-2 animate-pulse delay-150"><Scale size={16} className="text-amber-500"/> Applying Actuarial Math</p>
                </div>
              </div>
            </div>
          )}

          {result && !isProcessing && isResultsStep && (
            <div className="flex flex-col gap-6 h-full animate-in fade-in slide-in-from-bottom-4 duration-500">
              
              <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
                <div className="bg-slate-900 p-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 text-white">
                  <div>
                    <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Final Adjudication Status</h2>
                    <div className="flex items-center gap-3 mt-2">
                      {result.decision === "APPROVED" && <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"><CheckCircle2 size={18}/> APPROVED</span>}
                      {result.decision === "PARTIAL" && <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30"><AlertTriangle size={18}/> PARTIAL APPROVAL</span>}
                      {result.decision === "MANUAL_REVIEW" && <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30"><ShieldCheck size={18}/> ROUTED TO REVIEW</span>}
                      {result.decision === "REJECTED" && <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30"><AlertCircle size={18}/> REJECTED</span>}
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-8">
                    <div className="text-right">
                      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">AI Confidence</p>
                      <span className={`text-3xl font-black tracking-tight ${result.confidence_score >= 0.8 ? 'text-emerald-400' : 'text-amber-400'}`}>
                        {result.confidence_score ? (result.confidence_score * 100).toFixed(0) + '%' : 'N/A'}
                      </span>
                    </div>
                    <div className="text-right border-l border-slate-700 pl-8">
                      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Approved Payout</p>
                      <span className="text-4xl font-black text-white tracking-tight">
                        ₹{(result.approved_amount || 0).toLocaleString('en-IN')}
                      </span>
                    </div>
                  </div>
                </div>
                
                <div className="p-6 grid grid-cols-3 gap-4 border-b border-slate-100 bg-slate-50">
                  <div>
                    <p className="text-xs font-semibold text-slate-500 uppercase">Claimed Amount</p>
                    <p className="text-lg font-bold text-slate-800">₹{Number(formData.claimedAmount).toLocaleString('en-IN')}</p>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-slate-500 uppercase">Patient Liability</p>
                    <p className="text-lg font-bold text-rose-600">
                      ₹{Math.max(0, Number(formData.claimedAmount) - (result.approved_amount || 0)).toLocaleString('en-IN')}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-slate-500 uppercase">Processing Time</p>
                    <p className="text-lg font-bold text-slate-800">{'< 4.2s'}</p>
                  </div>
                </div>

                <div className="p-6">
                  {(result.rejection_reasons?.length > 0 || result.fraud_flags?.length > 0 || result.notes) && (
                    <div className="bg-slate-50 p-5 rounded-xl border border-slate-200">
                      {(result.rejection_reasons?.length > 0 || result.fraud_flags?.length > 0) && (
                        <div className="mb-4">
                          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-2">System Flags Triggered</span>
                          <div className="flex flex-wrap gap-2">
                            {[...(result.rejection_reasons || []), ...(result.fraud_flags || [])].map((reason: string, i: number) => (
                              <span key={i} className="text-xs font-bold bg-rose-100 text-rose-700 border border-rose-200 px-2.5 py-1 rounded shadow-sm">
                                {reason.replace(/_/g, ' ')}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {result.notes && (
                        <div>
                          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-1">Actuarial Notes</span>
                          <p className="text-sm font-medium text-slate-700 leading-relaxed border-l-2 border-indigo-500 pl-3">{result.notes}</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {result.itemized_breakdown?.length > 0 && (
                <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
                  <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex items-center gap-2">
                    <Receipt size={18} className="text-slate-500"/>
                    <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider">Itemized Medical Metrics</h3>
                  </div>
                  <div className="divide-y divide-slate-100">
                    {result.itemized_breakdown.map((item: any, idx: number) => (
                      <div key={idx} className="p-4 px-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-50 transition-colors">
                        <div className="flex flex-col">
                          <span className="text-sm font-semibold text-slate-800">{item.item}</span>
                          {item.status === "REJECTED" && (
                            <span className="text-xs font-bold text-rose-500 mt-1 flex items-center gap-1"><X size={12}/> {item.reason || "Excluded from Policy"}</span>
                          )}
                        </div>
                        <div className="flex items-center gap-4 sm:min-w-[150px] justify-between sm:justify-end">
                          {item.status === "APPROVED" ? (
                            <span className="text-[10px] font-black tracking-widest text-emerald-700 bg-emerald-100 px-2 py-1 rounded uppercase">Apprvd</span>
                          ) : (
                            <span className="text-[10px] font-black tracking-widest text-rose-700 bg-rose-100 px-2 py-1 rounded uppercase">Denied</span>
                          )}
                          <span className={`text-base font-bold w-20 text-right ${item.status === "APPROVED" ? "text-slate-900" : "text-slate-300 line-through"}`}>
                            ₹{item.approved_amt || 0}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {isDevMode && (
                <div className="bg-slate-950 rounded-2xl shadow-2xl overflow-hidden flex flex-col border border-slate-800 animate-in fade-in slide-in-from-top-4">
                  <div className="bg-slate-900 px-4 py-3 flex items-center justify-between border-b border-slate-800">
                    <div className="flex gap-2">
                      <div className="w-3 h-3 rounded-full bg-rose-500"></div>
                      <div className="w-3 h-3 rounded-full bg-amber-500"></div>
                      <div className="w-3 h-3 rounded-full bg-emerald-500"></div>
                    </div>
                    <span className="text-xs font-bold text-emerald-400 font-mono tracking-widest flex items-center gap-2">
                      <Terminal size={14}/> SYSTEM_TRACE_LOG.json
                    </span>
                    <div className="w-12"></div>
                  </div>
                  <div className="p-6 overflow-auto max-h-[400px] custom-scrollbar">
                    <pre className="text-[12px] leading-relaxed font-mono text-slate-300">
                      {JSON.stringify(result, null, 2)}
                    </pre>
                  </div>
                </div>
              )}

            </div>
          )}
        </div>
      </main>
    </div>
  );
}