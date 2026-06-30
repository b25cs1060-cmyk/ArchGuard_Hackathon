export interface StaticIssue {
  severity: "critical" | "high" | "medium" | "low";
  rule: string;
  file: string;
  line: number;
  message: string;
}

export interface EnrichedFinding {
  title: string;
  reasoning: string;
  confidence: number;
  category: string;
}

export interface HistoricalContext {
  similar_incident: string;
  date: string;
  outcome: string;
  link?: string;
}

export interface AnalysisResult {
  pr_url: string;
  pr_title: string;
  should_rollback: boolean;
  overall_risk_score: number; // 0-10
  summary: string;
  static_analysis: {
    issue_count: number;
    details: StaticIssue[];
  };
  enriched_findings: EnrichedFinding[];
  historical_context: HistoricalContext[];
}

// Deterministic-ish mock — varies based on URL + context so demo feels alive.
export function generateMockAnalysis(prUrl: string, context: string): AnalysisResult {
  const hay = (prUrl + context).toLowerCase();
  const dangerous =
    hay.includes("auth") ||
    hay.includes("password") ||
    hay.includes("payment") ||
    hay.includes("prod") ||
    hay.length % 3 === 0;

  if (dangerous) {
    return {
      pr_url: prUrl,
      pr_title: "feat(auth): refactor session handling and rate limits",
      should_rollback: true,
      overall_risk_score: 8.7,
      summary:
        "High-risk change touching authentication boundaries with a hardcoded secret and a missing rate limiter on a public endpoint. Historically similar PRs caused outages.",
      static_analysis: {
        issue_count: 4,
        details: [
          {
            severity: "critical",
            rule: "hardcoded-secret",
            file: "src/server/auth.ts",
            line: 42,
            message: "Hardcoded API token detected. Move to environment variable.",
          },
          {
            severity: "high",
            rule: "missing-rate-limit",
            file: "src/routes/api/login.ts",
            line: 18,
            message: "Public login endpoint has no rate limiter — vulnerable to credential stuffing.",
          },
          {
            severity: "high",
            rule: "sql-injection-risk",
            file: "src/db/users.ts",
            line: 87,
            message: "String concatenation in SQL query. Use parameterized statements.",
          },
          {
            severity: "medium",
            rule: "missing-error-boundary",
            file: "src/components/Checkout.tsx",
            line: 12,
            message: "Component fetches data without error handling.",
          },
        ],
      },
      enriched_findings: [
        {
          title: "Session invalidation gap",
          reasoning:
            "The refactor changes the order of token verification and session lookup. Existing sessions issued before deploy may bypass the new MFA check for a 5-minute window.",
          confidence: 0.92,
          category: "Security",
        },
        {
          title: "N+1 query introduced",
          reasoning:
            "The new `getUserPermissions` loop calls the DB per role. Expect ~40x latency increase for users with 10+ roles.",
          confidence: 0.81,
          category: "Performance",
        },
        {
          title: "Breaking API contract",
          reasoning:
            "`POST /api/session` response shape changed (`token` → `access_token`). Mobile clients on v2.3.x will crash on parse.",
          confidence: 0.88,
          category: "Compatibility",
        },
      ],
      historical_context: [
        {
          similar_incident: "PR #2841 — auth middleware reorder",
          date: "2025-03-14",
          outcome: "Caused 47-min outage. Rolled back after PagerDuty alert.",
        },
        {
          similar_incident: "PR #3102 — login rate limit removal",
          date: "2025-05-02",
          outcome: "Credential stuffing attack within 6 hours of deploy. 12k accounts locked.",
        },
      ],
    };
  }

  return {
    pr_url: prUrl,
    pr_title: "chore(ui): polish dashboard spacing and copy",
    should_rollback: false,
    overall_risk_score: 1.4,
    summary:
      "Low-risk presentation-only change. No server, auth, or database surface touched. Test coverage holds.",
    static_analysis: {
      issue_count: 1,
      details: [
        {
          severity: "low",
          rule: "unused-import",
          file: "src/components/Dashboard.tsx",
          line: 7,
          message: "`useEffect` imported but not used.",
        },
      ],
    },
    enriched_findings: [
      {
        title: "Visual regression risk: minimal",
        reasoning:
          "Changes are confined to Tailwind class adjustments. No layout primitives touched.",
        confidence: 0.95,
        category: "UI",
      },
      {
        title: "Bundle size neutral",
        reasoning: "Net diff is -3 LOC. No new dependencies imported.",
        confidence: 0.99,
        category: "Performance",
      },
    ],
    historical_context: [
      {
        similar_incident: "PR #3340 — dashboard spacing pass",
        date: "2025-06-11",
        outcome: "Merged clean. Zero post-deploy incidents.",
      },
    ],
  };
}
