import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Loader2,
  ShieldCheck,
  GitPullRequest,
  Activity,
  FileWarning,
  Brain,
  History,
} from "lucide-react";
import { generateMockAnalysis, type AnalysisResult, type StaticIssue } from "@/lib/mock-analysis";
import logoAsset from "@/assets/archguard-logo.png.asset.json";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Archguard — AI PR Risk Analyzer" },
      {
        name: "description",
        content:
          "Decide whether to merge or rollback. AI-assisted static analysis, historical incident matching, and a single verdict for every PR.",
      },
      { property: "og:title", content: "Archguard — AI PR Risk Analyzer" },
      {
        property: "og:description",
        content:
          "Decide whether to merge or rollback. AI-assisted static analysis, historical incident matching, and a single verdict for every PR.",
      },
    ],
  }),
  component: Index,
});

function Index() {
  const [prUrl, setPrUrl] = useState("");
  const [context, setContext] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [tab, setTab] = useState<"static" | "ai">("static");

  async function handleAnalyze(e: React.FormEvent) {
    e.preventDefault();
    if (!prUrl.trim() || loading) return;
    setLoading(true);
    setResult(null);
    // Simulate AI pipeline latency
    await new Promise((r) => setTimeout(r, 1800));
    setResult(generateMockAnalysis(prUrl, context));
    setLoading(false);
  }

  return (
    <main className="min-h-screen">
      {/* Top bar */}
      <header className="border-b border-border/60 backdrop-blur-sm sticky top-0 z-30 bg-background/70">
        <div className="max-w-7xl mx-auto px-6 py-6 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <img
              src={logoAsset.url}
              alt="Archguard logo"
              className="h-16 md:h-20 w-auto"
            />
            <div className="text-center">
              <div className="font-mono text-3xl md:text-4xl font-black tracking-tight">
                ARCHGUARD
              </div>
              <div className="text-xs uppercase tracking-[0.25em] text-muted-foreground">
                AI PR Risk Analyzer
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* ZONE 1 — Input Dashboard */}
        <InputZone
          prUrl={prUrl}
          setPrUrl={setPrUrl}
          context={context}
          setContext={setContext}
          loading={loading}
          onSubmit={handleAnalyze}
        />

        {/* Loading state */}
        {loading && <LoadingState />}

        {/* ZONE 2 + 3 — Results */}
        {result && !loading && (
          <>
            <VerdictZone result={result} />
            <ReceiptsZone result={result} tab={tab} setTab={setTab} />
          </>
        )}

        {!result && !loading && <EmptyState />}
      </div>

      <footer className="border-t border-border/60 mt-16">
        <div className="max-w-7xl mx-auto px-6 py-6 font-mono text-xs text-muted-foreground flex items-center justify-between">
          <span>// built for the merge-or-perish hackathon</span>
          <span>v0.1.0-alpha</span>
        </div>
      </footer>
    </main>
  );
}

/* ---------- ZONE 1 ---------- */

function InputZone({
  prUrl,
  setPrUrl,
  context,
  setContext,
  loading,
  onSubmit,
}: {
  prUrl: string;
  setPrUrl: (v: string) => void;
  context: string;
  setContext: (v: string) => void;
  loading: boolean;
  onSubmit: (e: React.FormEvent) => void;
}) {
  return (
    <section className="relative overflow-hidden rounded-xl border border-border bg-card shadow-elevated">
      <div className="absolute inset-0 grid-bg opacity-40 pointer-events-none" />
      <div className="relative p-6 md:p-8">
        <h1 className="font-mono text-2xl md:text-3xl font-bold tracking-tight">
          Should we <span className="text-destructive">rollback</span> or{" "}
          <span className="text-primary">merge</span>?
        </h1>
        <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
          Paste a pull request, add any context the AI should weigh, and get a verdict in seconds.
        </p>

        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <div>
            <label className="block font-mono text-sm font-bold uppercase tracking-[0.2em] text-primary mb-2">
              Pull Request URL
            </label>
            <div className="relative">
              <GitPullRequest className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                type="url"
                required
                value={prUrl}
                onChange={(e) => setPrUrl(e.target.value)}
                placeholder="https://github.com/acme/api/pull/2841"
                disabled={loading}
                className="w-full pl-10 pr-3 py-3 rounded-md bg-input border border-border font-mono text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring transition disabled:opacity-50"
              />
            </div>
          </div>

          <div className="rounded-lg border border-border bg-muted/30 p-4">
            <label className="block font-mono text-sm font-bold uppercase tracking-[0.2em] text-primary mb-2">
              Questions
            </label>
            <div className="min-h-[80px] rounded-md border border-border bg-background/60 p-3 font-mono text-sm text-muted-foreground" />
          </div>

          <div className="rounded-lg border border-border bg-muted/30 p-4">
            <label className="block font-mono text-sm font-bold uppercase tracking-[0.2em] text-primary mb-2">
              Answers
            </label>
            <textarea
              value={context}
              onChange={(e) => setContext(e.target.value)}
              rows={4}
              disabled={loading}
              placeholder="please type in your answers here"
              className="w-full px-3 py-3 rounded-md bg-input border border-border font-mono text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring transition resize-none disabled:opacity-50"
            />
          </div>

          <div className="flex items-center justify-end gap-4 pt-2">
            <button
              type="submit"
              disabled={loading || !prUrl.trim()}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-md bg-primary text-primary-foreground font-mono text-sm font-semibold tracking-tight hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  ANALYZING...
                </>
              ) : (
                <>
                  <Activity className="w-4 h-4" />
                  RUN ANALYSIS
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}

/* ---------- LOADING ---------- */

function LoadingState() {
  const steps = [
    "Cloning PR diff",
    "Running static analyzers",
    "Enriching with LLM reasoning",
    "Matching against incident history",
    "Computing risk score",
  ];
  return (
    <section className="relative overflow-hidden rounded-xl border border-border bg-card p-8">
      <div className="absolute inset-x-0 h-px bg-gradient-to-r from-transparent via-primary to-transparent top-0 animate-scan" />
      <div className="flex items-center gap-3 mb-6">
        <Loader2 className="w-5 h-5 text-primary animate-spin" />
        <div className="font-mono text-sm uppercase tracking-[0.2em] text-primary">
          analyzing pull request
        </div>
      </div>
      <ul className="space-y-3 font-mono text-sm">
        {steps.map((s, i) => (
          <li
            key={s}
            className="flex items-center gap-3 text-muted-foreground"
            style={{ animation: `pulse 1.4s ease-in-out ${i * 0.18}s infinite` }}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-primary" />
            <span>{s}...</span>
          </li>
        ))}
      </ul>
      <div className="mt-6 space-y-2">
        <div className="h-3 rounded bg-muted/50 overflow-hidden">
          <div className="h-full w-1/3 bg-primary/40 animate-pulse" />
        </div>
        <div className="h-3 rounded bg-muted/50 overflow-hidden">
          <div className="h-full w-2/3 bg-primary/30 animate-pulse" />
        </div>
        <div className="h-3 rounded bg-muted/50 overflow-hidden">
          <div className="h-full w-1/2 bg-primary/20 animate-pulse" />
        </div>
      </div>
    </section>
  );
}

/* ---------- ZONE 2 — VERDICT ---------- */

function VerdictZone({ result }: { result: AnalysisResult }) {
  const danger = result.should_rollback;
  return (
    <section className="space-y-4">
      <div className="flex items-center gap-2 font-mono text-xs text-muted-foreground">
        <span className="uppercase tracking-[0.2em]">zone 02 / verdict</span>
      </div>

      <div
        className={[
          "relative overflow-hidden rounded-2xl border-2 p-8 md:p-12",
          danger
            ? "border-destructive/60 bg-destructive/5 animate-pulse-danger"
            : "border-primary/60 bg-primary/5 animate-pulse-safe",
        ].join(" ")}
      >
        <div className="absolute inset-0 grid-bg opacity-30 pointer-events-none" />

        <div className="relative grid md:grid-cols-[1fr_auto] gap-8 items-center">
          <div>
            <div
              className={[
                "inline-flex items-center gap-2 px-3 py-1 rounded-full font-mono text-[10px] uppercase tracking-[0.2em] mb-4",
                danger
                  ? "bg-destructive/20 text-destructive border border-destructive/40"
                  : "bg-primary/20 text-primary border border-primary/40",
              ].join(" ")}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
              verdict
            </div>
            <h2
              className={[
                "font-mono font-extrabold tracking-tighter leading-none text-4xl md:text-6xl lg:text-7xl",
                danger ? "text-destructive" : "text-primary",
              ].join(" ")}
            >
              {danger ? (
                <span className="inline-flex items-center gap-4">
                  <XCircle className="w-12 h-12 md:w-16 md:h-16" />
                  ROLLBACK
                </span>
              ) : (
                <span className="inline-flex items-center gap-4">
                  <CheckCircle2 className="w-12 h-12 md:w-16 md:h-16" />
                  SAFE TO MERGE
                </span>
              )}
            </h2>
            <p
              className={[
                "font-mono text-sm md:text-base mt-4 uppercase tracking-[0.15em]",
                danger ? "text-destructive/80" : "text-primary/80",
              ].join(" ")}
            >
              {danger ? "do not deploy — review immediately" : "ship it"}
            </p>
            <p className="text-sm md:text-base text-foreground/80 mt-6 max-w-2xl leading-relaxed">
              {result.summary}
            </p>

            <div className="mt-6 flex items-center gap-2 font-mono text-xs text-muted-foreground">
              <GitPullRequest className="w-3.5 h-3.5" />
              <span className="truncate">{result.pr_title}</span>
            </div>
          </div>

          <RiskGauge score={result.overall_risk_score} danger={danger} />
        </div>
      </div>
    </section>
  );
}

function RiskGauge({ score, danger }: { score: number; danger: boolean }) {
  const pct = Math.min(100, (score / 10) * 100);
  const color = danger ? "var(--color-destructive)" : "var(--color-primary)";
  return (
    <div className="w-full md:w-[280px] shrink-0">
      <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-3 text-center md:text-right">
        risk score
      </div>
      <div className="flex items-baseline justify-center md:justify-end gap-1">
        <span
          className="font-mono font-extrabold text-6xl md:text-7xl tabular-nums leading-none"
          style={{ color }}
        >
          {score.toFixed(1)}
        </span>
        <span className="font-mono text-xl text-muted-foreground">/10</span>
      </div>

      <div className="mt-4 relative h-3 rounded-full bg-muted/60 overflow-hidden border border-border">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{
            width: `${pct}%`,
            background: `linear-gradient(90deg, ${color}, color-mix(in oklab, ${color} 60%, transparent))`,
            boxShadow: `0 0 12px ${color}`,
          }}
        />
      </div>
      <div className="mt-2 flex justify-between font-mono text-[10px] text-muted-foreground">
        <span>0 SAFE</span>
        <span>5 WATCH</span>
        <span>10 STOP</span>
      </div>
    </div>
  );
}

/* ---------- ZONE 3 — RECEIPTS ---------- */

function ReceiptsZone({
  result,
  tab,
  setTab,
}: {
  result: AnalysisResult;
  tab: "static" | "ai";
  setTab: (t: "static" | "ai") => void;
}) {
  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 font-mono text-xs text-muted-foreground">
          <span className="uppercase tracking-[0.2em]">zone 03 / receipts</span>
        </div>
        <div className="font-mono text-[11px] text-muted-foreground">
          {result.static_analysis.issue_count} static · {result.enriched_findings.length} insights ·{" "}
          {result.historical_context.length} precedents
        </div>
      </div>

      <div className="flex gap-1 border-b border-border">
        <TabButton active={tab === "static"} onClick={() => setTab("static")}>
          <FileWarning className="w-4 h-4" />
          Static Issues
          <span className="ml-1 px-1.5 py-0.5 rounded text-[10px] bg-muted text-muted-foreground tabular-nums">
            {result.static_analysis.issue_count}
          </span>
        </TabButton>
        <TabButton active={tab === "ai"} onClick={() => setTab("ai")}>
          <Brain className="w-4 h-4" />
          AI Insights
          <span className="ml-1 px-1.5 py-0.5 rounded text-[10px] bg-muted text-muted-foreground tabular-nums">
            {result.enriched_findings.length + result.historical_context.length}
          </span>
        </TabButton>
      </div>

      {tab === "static" ? (
        <StaticIssuesPanel issues={result.static_analysis.details} />
      ) : (
        <AIInsightsPanel
          findings={result.enriched_findings}
          history={result.historical_context}
        />
      )}
    </section>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={[
        "inline-flex items-center gap-2 px-4 py-2.5 font-mono text-xs uppercase tracking-[0.15em] border-b-2 -mb-px transition",
        active
          ? "border-primary text-primary"
          : "border-transparent text-muted-foreground hover:text-foreground",
      ].join(" ")}
    >
      {children}
    </button>
  );
}

function severityStyles(sev: StaticIssue["severity"]) {
  switch (sev) {
    case "critical":
      return {
        border: "border-destructive/50",
        bg: "bg-destructive/10",
        text: "text-destructive",
        label: "CRITICAL",
      };
    case "high":
      return {
        border: "border-destructive/40",
        bg: "bg-destructive/5",
        text: "text-destructive",
        label: "HIGH",
      };
    case "medium":
      return {
        border: "border-warning/40",
        bg: "bg-warning/5",
        text: "text-warning",
        label: "MEDIUM",
      };
    case "low":
      return {
        border: "border-border",
        bg: "bg-muted/30",
        text: "text-muted-foreground",
        label: "LOW",
      };
  }
}

function StaticIssuesPanel({ issues }: { issues: StaticIssue[] }) {
  if (issues.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-card p-8 text-center text-muted-foreground font-mono text-sm">
        <ShieldCheck className="w-8 h-8 mx-auto mb-2 text-primary" />
        No static issues found.
      </div>
    );
  }
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {issues.map((issue, i) => {
        const s = severityStyles(issue.severity);
        return (
          <div
            key={i}
            className={`relative rounded-lg border ${s.border} ${s.bg} p-5 transition hover:translate-y-[-1px]`}
          >
            <div className="flex items-start justify-between gap-3 mb-2">
              <div className={`inline-flex items-center gap-1.5 font-mono text-[10px] font-bold tracking-[0.15em] ${s.text}`}>
                <AlertTriangle className="w-3 h-3" />
                {s.label}
              </div>
              <code className="font-mono text-[10px] text-muted-foreground bg-background/50 px-2 py-0.5 rounded">
                {issue.rule}
              </code>
            </div>
            <div className="font-mono text-xs text-muted-foreground mb-2 truncate">
              {issue.file}:{issue.line}
            </div>
            <p className="text-sm text-foreground/90 leading-relaxed">{issue.message}</p>
          </div>
        );
      })}
    </div>
  );
}

function AIInsightsPanel({
  findings,
  history,
}: {
  findings: AnalysisResult["enriched_findings"];
  history: AnalysisResult["historical_context"];
}) {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="space-y-3">
        <div className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground flex items-center gap-2">
          <Brain className="w-3.5 h-3.5" /> enriched findings
        </div>
        {findings.map((f, i) => (
          <div key={i} className="rounded-lg border border-border bg-card p-5">
            <div className="flex items-center justify-between gap-3 mb-2">
              <h4 className="font-mono text-sm font-semibold">{f.title}</h4>
              <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-accent/15 text-accent border border-accent/30">
                {f.category}
              </span>
            </div>
            <p className="text-sm text-foreground/80 leading-relaxed">{f.reasoning}</p>
            <div className="mt-3 flex items-center gap-2">
              <div className="flex-1 h-1 rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full bg-accent"
                  style={{ width: `${f.confidence * 100}%` }}
                />
              </div>
              <span className="font-mono text-[10px] text-muted-foreground tabular-nums">
                {(f.confidence * 100).toFixed(0)}% conf.
              </span>
            </div>
          </div>
        ))}
      </div>

      <div className="space-y-3">
        <div className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground flex items-center gap-2">
          <History className="w-3.5 h-3.5" /> historical context
        </div>
        {history.map((h, i) => (
          <div key={i} className="rounded-lg border border-border bg-card p-5">
            <div className="flex items-center justify-between gap-3 mb-2">
              <h4 className="font-mono text-sm font-semibold">{h.similar_incident}</h4>
              <span className="font-mono text-[10px] text-muted-foreground tabular-nums">
                {h.date}
              </span>
            </div>
            <p className="text-sm text-foreground/80 leading-relaxed">{h.outcome}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------- EMPTY ---------- */

function EmptyState() {
  return (
    <section className="rounded-xl border border-dashed border-border bg-card/40 p-10 text-center">
      <div className="w-12 h-12 rounded-lg bg-primary/10 border border-primary/20 grid place-items-center mx-auto mb-4">
        <Activity className="w-6 h-6 text-primary" />
      </div>
      <h3 className="font-mono text-sm font-semibold mb-1">No analysis yet</h3>
      <p className="text-sm text-muted-foreground max-w-md mx-auto">
        Paste a PR URL above. The pipeline returns a verdict, a risk score, and the receipts that
        justify it.
      </p>
    </section>
  );
}
