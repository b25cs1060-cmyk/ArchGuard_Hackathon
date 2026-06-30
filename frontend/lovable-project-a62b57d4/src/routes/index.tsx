import { createFileRoute } from "@tanstack/react-router";
import React, { useState } from "react";
import { RotateCcw, Loader2, GitPullRequest, Activity, CheckCircle2 } from "lucide-react";
import { analyzePR, submitAnswers, enforceRollback } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import archguardLogo from "@/assets/archguard-logo.png";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [{ title: "Archguard — AI PR Risk Analyzer" }],
  }),
  component: Index,
});

type BackendResult = {
  should_rollback: boolean;
  overall_risk_score: number;
  data: {
    ai_review: {
      static_findings: any[];
      enriched_findings: string;
      historical_context: string;
      scenarios: string;
    };
  };
};

function Index() {
  const [prUrl, setPrUrl] = useState("");
  const [questions, setQuestions] = useState<string[]>([]);
  const [context, setContext] = useState("");
  const [step, setStep] = useState<"idle" | "fetching_questions" | "answering" | "analyzing" | "done">("idle");
  const [result, setResult] = useState<BackendResult | null>(null);
  const [tab, setTab] = useState<"static" | "ai">("static");

  async function handleGetQuestions(e: React.FormEvent) {
    e.preventDefault();
    if (!prUrl.trim() || step === "fetching_questions") return;
    setStep("fetching_questions");
    try {
      const res = await analyzePR(prUrl);
      const raw = res.questions_for_developer || [];
      
      // LOGIC FIX: Strip out intro sentences so only questions remain
      const cleanList = (Array.isArray(raw) ? raw : [raw])
        .flatMap(q => q.split(/\n/))
        .map(q => q.replace(/^\d+\.\s*/, "")) // Remove existing numbering if present
        .filter(q => q.trim().length > 0)
        .filter(q => !q.toLowerCase().includes("here are") && !q.toLowerCase().includes("here is"));
      
      setQuestions(cleanList);
      setStep("answering");
    } catch (error) {
      alert("Failed to analyze PR.");
      setStep("idle");
    }
  }

  async function handleRunAnalysis(e: React.FormEvent) {
    e.preventDefault();
    if (!context.trim() || step === "analyzing") return;
    setStep("analyzing");
    try {
      const res = await submitAnswers(prUrl, context);
      setResult(res);
      setStep("done");
    } catch (error) {
      alert("Failed to run full analysis.");
      setStep("answering");
    }
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border/60 sticky top-0 z-30 bg-background/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 py-6 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3">
             <div className="w-20 h-20 rounded-2xl flex items-center justify-center">
                <img src={archguardLogo} alt="Archguard Logo" className="w-full h-full object-contain" />
             </div>
            <div className="text-center">
              <div className="font-mono text-3xl font-black">ARCHGUARD</div>
              <div className="text-xs uppercase tracking-[0.25em] text-muted-foreground">AI PR Risk Analyzer</div>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {step !== "done" && (
          <InputZone prUrl={prUrl} setPrUrl={setPrUrl} questions={questions} context={context} setContext={setContext} step={step} onGetQuestions={handleGetQuestions} onRunAnalysis={handleRunAnalysis} />
        )}
        {(step === "fetching_questions" || step === "analyzing") && <LoadingState step={step} />}
        {step === "done" && result && (
          <>
            <VerdictZone result={result} prUrl={prUrl} />
            <ReceiptsZone result={result} tab={tab} setTab={setTab} />
          </>
        )}
        {step === "idle" && <EmptyState />}
      </div>
    </main>
  );
}

function InputZone({ prUrl, setPrUrl, questions, context, setContext, step, onGetQuestions, onRunAnalysis }: any) {
  return (
    <section className="rounded-xl border border-border bg-card p-8 shadow-sm">
      <h1 className="font-mono text-2xl font-bold mb-8">Should we <span className="text-destructive">rollback</span> or <span className="text-primary">merge</span>?</h1>
      {step === "idle" || step === "fetching_questions" ? (
        <form onSubmit={onGetQuestions} className="space-y-4">
          <label className="block font-mono text-xs uppercase tracking-widest text-muted-foreground">Pull Request URL</label>
          <input type="url" required value={prUrl} onChange={(e) => setPrUrl(e.target.value)} disabled={step === "fetching_questions"} className="w-full px-4 py-3 rounded-md bg-input border border-border font-mono text-sm" placeholder="https://github.com/..." />
          <div className="flex justify-end"><button type="submit" className="px-6 py-3 rounded-md bg-primary text-primary-foreground font-mono font-bold hover:opacity-90">{step === "fetching_questions" ? "SCANNING..." : "GET QUESTIONS"}</button></div>
        </form>
      ) : (
        <form onSubmit={onRunAnalysis} className="space-y-8">
           <div className="space-y-4">
            <label className="block font-mono text-xs uppercase tracking-widest text-primary mb-4">AI Diagnostic Questions</label>
            <div className="flex flex-col gap-4">
                {questions.map((q: string, i: number) => (
                    <div key={i} className="flex gap-4 p-5 rounded-lg border border-border bg-muted/20 items-start hover:border-primary/50 transition-colors">
                        <span className="font-mono font-black text-primary text-lg shrink-0">Q{i + 1}.</span>
                        <p className="font-mono text-sm text-foreground/90 leading-relaxed">{q}</p>
                    </div>
                ))}
            </div>
          </div>
          <textarea required value={context} onChange={(e) => setContext(e.target.value)} rows={6} className="w-full px-4 py-3 rounded-md bg-input border border-border font-mono text-sm" placeholder="Please provide your answers here..." />
          <div className="flex justify-end"><button type="submit" className="px-6 py-3 rounded-md bg-primary text-primary-foreground font-mono font-bold hover:opacity-90">{step === "analyzing" ? "ANALYZING..." : "RUN FULL ANALYSIS"}</button></div>
        </form>
      )}
    </section>
  );
}

function VerdictZone({ result, prUrl }: any) {
  const danger = result?.should_rollback;
  const [rollingBack, setRollingBack] = useState(false);
  const [rollbackComplete, setRollbackComplete] = useState(false);

  const executeRollback = async () => {
    setRollingBack(true);
    try {
      await enforceRollback(prUrl, result.overall_risk_score, result.data.ai_review.scenarios);
      setRollbackComplete(true);
    } catch (e) { alert("Failed to execute rollback."); }
    setRollingBack(false);
  };

  return (
    <section className="rounded-2xl border-2 p-10 md:p-12" style={{ borderColor: danger ? 'var(--color-destructive)' : 'var(--color-primary)', background: danger ? 'rgba(239, 68, 68, 0.05)' : 'rgba(16, 185, 129, 0.05)' }}>
      <div className="grid lg:grid-cols-[1fr,auto] gap-12 items-start">
        <div className="min-w-0">
          <h2 className="font-mono font-extrabold text-5xl mb-6" style={{ color: danger ? 'var(--color-destructive)' : 'var(--color-primary)' }}>
            {danger ? "ROLLBACK" : "SAFE TO MERGE"}
          </h2>
          <div className="prose prose-lg prose-invert max-w-none text-foreground/90">
             <p className="leading-relaxed font-medium">{result?.data?.ai_review?.scenarios || "No scenario details."}</p>
          </div>
          {danger && (
            <div className="mt-10">
              {rollbackComplete ? (
                <div className="inline-flex items-center gap-3 px-6 py-4 bg-green-500/10 text-green-400 border border-green-500/30 font-mono font-bold rounded-lg">
                  <CheckCircle2 className="w-6 h-6" /> ROLLBACK SUCCESSFULLY ENFORCED
                </div>
              ) : (
                <button onClick={executeRollback} disabled={rollingBack} className="flex items-center gap-2 px-8 py-4 bg-destructive text-destructive-foreground font-mono font-bold rounded-lg hover:opacity-90 transition shadow-lg shadow-destructive/20">
                  <RotateCcw className={rollingBack ? "animate-spin" : ""} /> {rollingBack ? "ENFORCING..." : "ENFORCE AUTOMATED ROLLBACK"}
                </button>
              )}
            </div>
          )}
        </div>
        <div className="bg-background/50 p-8 rounded-2xl border border-border flex flex-col items-center justify-center shrink-0">
            <div className="font-mono text-[10px] uppercase text-muted-foreground mb-2">Risk Score</div>
            <div className="font-mono font-extrabold text-8xl" style={{ color: danger ? 'var(--color-destructive)' : 'var(--color-primary)' }}>
                {result?.overall_risk_score?.toFixed(1)}
            </div>
            <div className="text-muted-foreground font-mono text-sm mt-1">/ 10.0</div>
        </div>
      </div>
    </section>
  );
}

function ReceiptsZone({ result, tab, setTab }: any) {
  const issues = result?.data?.ai_review?.static_findings || [];
  return (
    <section className="mt-8">
      <div className="flex gap-6 border-b border-border mb-6">
        <button className={`pb-2 font-mono text-sm ${tab === "static" ? "border-b-2 border-primary text-primary" : "text-muted-foreground"}`} onClick={() => setTab("static")}>Static Issues ({issues.length})</button>
        <button className={`pb-2 font-mono text-sm ${tab === "ai" ? "border-b-2 border-primary text-primary" : "text-muted-foreground"}`} onClick={() => setTab("ai")}>AI Analysis Context</button>
      </div>
      {tab === "static" ? (
        <div className="grid gap-3 md:grid-cols-2">
          {issues.map((issue: any, i: number) => (
            <div key={i} className="rounded-lg border border-border bg-card p-5 transition hover:translate-y-[-1px]">
               <div className="flex justify-between items-start mb-2">
                 <code className="text-[10px] bg-muted px-2 py-1 rounded text-primary">{issue.pattern}</code>
                 <span className="text-[10px] text-muted-foreground font-mono">{issue.file}</span>
               </div>
               <p className="text-sm text-foreground/90">{issue.description}</p>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-6">
          <div className="p-6 border rounded bg-card prose prose-invert prose-sm max-w-none">
            <h4 className="text-primary font-mono text-xs uppercase mb-3">Blast Radius Analysis</h4>
            <ReactMarkdown components={{ h3: ({node, ...props}) => <h3 className="text-primary font-bold mt-4" {...props} /> }}>
              {result?.data?.ai_review?.enriched_findings || ""}
            </ReactMarkdown>
          </div>
          <div className="p-6 border rounded bg-card">
            <h4 className="font-mono text-primary uppercase text-xs mb-3">Historical Context</h4>
            <p className="text-sm text-foreground/80 leading-relaxed">{result?.data?.ai_review?.historical_context}</p>
          </div>
        </div>
      )}
    </section>
  );
}

function LoadingState({ step }: { step: string }) {
  return <div className="p-8 text-center font-mono text-primary animate-pulse">{step === "fetching_questions" ? "PARSING PR..." : "ANALYZING..."}</div>;
}

function EmptyState() {
  return <div className="p-10 text-center border-dashed border rounded opacity-50 font-mono">Awaiting Input</div>;
}