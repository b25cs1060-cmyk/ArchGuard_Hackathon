// Hardcoded to guarantee a connection for your local demo
const API_BASE_URL = import.meta.env.VITE_BACKEND_URL || "http://127.0.0.1:8000";

export const analyzePR = async (prUrl: string) => {
  const response = await fetch(`${API_BASE_URL}/analyze-pr`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pr_url: prUrl }),
  });
  
  if (!response.ok) throw new Error("Failed to analyze PR");
  return response.json();
};

export const submitAnswers = async (prUrl: string, developerAnswers: string) => {
  const response = await fetch(`${API_BASE_URL}/submit-answers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pr_url: prUrl, developer_answers: developerAnswers }),
  });

  if (!response.ok) throw new Error("Failed to submit answers");
  return response.json();
};

export const enforceRollback = async (prUrl: string, riskScore: number, reason: string) => {
  const response = await fetch(`${API_BASE_URL}/enforce-rollback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pr_url: prUrl, risk_score: riskScore, reason: reason }),
  });

  if (!response.ok) throw new Error("Failed to enforce rollback");
  return response.json();
};