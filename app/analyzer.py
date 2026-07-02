import re

class StaticAnalyzer:
    def __init__(self):
        self.findings = []

    def scan_python_code(self, filename: str, code: str):
        """Scans Python source code against backend anti-patterns."""
        if not code:
            return

        if "create_engine" in code and "pool_size" not in code:
            self._add_finding(1, "No DB connection pooling", 9, filename, "Found create_engine without pool_size configured.")

        if "async def" in code and re.search(r'(session\.query|db\.commit|requests\.(get|post))', code):
            if "await" not in code:
                self._add_finding(2, "Sync call in async handler", 8, filename, "Blocking call detected inside an async def.")

        if "@app." in code or "@router." in code:
            if "limiter" not in code and "SlowAPI" not in code:
                self._add_finding(3, "No rate limiting on routes", 7, filename, "FastAPI route detected without rate limiting.")

        if re.search(r'requests\.(get|post|put|delete)', code) and "@retry" not in code and "tenacity" not in code:
            self._add_finding(4, "Missing retry logic", 6, filename, "External HTTP call found without retry wrapper.")

        if re.search(r'\.query\(.*\)\.all\(\)', code):
            self._add_finding(5, "Unbounded query (no LIMIT)", 8, filename, ".all() called on a query which can crash memory on large tables.")

        if re.search(r'requests\.(get|post|put|delete)\(', code) and "timeout=" not in code:
            self._add_finding(6, "No timeout on HTTP calls", 7, filename, "requests call made without a strict timeout= parameter.")

        if "requests." in code and "CircuitBreaker" not in code and "pybreaker" not in code:
            self._add_finding(7, "No circuit breaker", 6, filename, "External API calls detected without a circuit breaker pattern.")

        if re.search(r'\.read\(\)', code) and "chunk" not in code:
            self._add_finding(9, "Large in-memory processing", 8, filename, "Using .read() on files without streaming chunks.")

        if "requests." in code and "try:" not in code and "except" not in code:
            self._add_finding(10, "No error handling on externals", 7, filename, "External call found outside of a try/except block.")

        secret_pattern = r'(?i)(password|secret|api_key|token)\s*=\s*["\'][a-zA-Z0-9_\-@!]{6,}["\']'
        if re.search(secret_pattern, code):
            self._add_finding(14, "Hardcoded secrets", 10, filename, "Potential hardcoded credential or token detected in source.")

        if ("def get_" in code or "def list_" in code) and ".all()" in code and "limit" not in code:
            self._add_finding(15, "No pagination on list endpoints", 7, filename, "List endpoint returns full table without pagination.")

    def scan_infra_code(self, filename: str, code: str):
        """Scans YAML, Kubernetes, and Docker configurations."""
        if not code:
            return

        is_k8s = "apiVersion:" in code or "kind: Deployment" in code

        if is_k8s:

            if "resources:" not in code or "limits:" not in code:
                self._add_finding(11, "No K8s resource limits", 9, filename, "Kubernetes YAML missing CPU/Memory resource limits.")

            if "readinessProbe:" not in code:
                self._add_finding(12, "No readiness probe", 7, filename, "Kubernetes YAML missing readinessProbe configuration.")

            if "replicas: 1" in code and "HorizontalPodAutoscaler" not in code:
                self._add_finding(13, "Single replica, no HPA", 8, filename, "Deployment stuck at 1 replica with no autoscaling.")

    def check_global_repo_rules(self, all_python_code: str):
        """Checks for missing architectural components across the whole codebase."""

        if "/health" not in all_python_code and "/ping" not in all_python_code:
            self._add_finding(8, "Missing health endpoint", 5, "Global", "No /health or /ping route detected for load balancers to check.")

    def _add_finding(self, rule_id: int, pattern: str, risk: int, file: str, description: str):
        self.findings.append({
            "rule_id": rule_id,
            "pattern": pattern,
            "risk_score": risk,
            "file": file,
            "description": description
        })

    def get_results(self) -> dict:

        sorted_findings = sorted(self.findings, key=lambda x: x["risk_score"], reverse=True)
        return {
            "total_issues": len(sorted_findings),
            "critical_issues": len([f for f in sorted_findings if f["risk_score"] >= 9]),
            "details": sorted_findings
        }

