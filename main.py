from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from github import Github
import uvicorn
import base64
import os
from dotenv import load_dotenv
from parser import analyze_python_file
from analyzer import StaticAnalyzer
from ai_agent import run_archguard_review  # Layer 3 integration

load_dotenv()

app = FastAPI(title="ArchGuard API")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN not found! Please check your .env file.")


class PRRequest(BaseModel):
    pr_url: str
    developer_context: str = "Standard deployment." 

class RollbackRequest(BaseModel):
    pr_url: str
    risk_score: float
    reason: str



@app.post("/analyze-pr")
async def analyze_pr_endpoint(request: PRRequest):
    print(f"Received URL: {request.pr_url}")
    

    try:
        parts = request.pr_url.rstrip('/').split('/')
        owner = parts[-4]
        repo_name = parts[-3]
        pr_number = int(parts[-1])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid GitHub PR URL format.")


    g = Github(GITHUB_TOKEN)
    try:
        repo = g.get_repo(f"{owner}/{repo_name}")
        pr = repo.get_pull(pr_number)
        print(f"Successfully fetched PR: '{pr.title}'")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Could not fetch PR. Error: {str(e)}")

    print("Extracting and Parsing files...")

    # 3. Layer 0 & 1: Extract and AST Parse
    changed_python_files = {}
    for file in pr.get_files():
        if file.filename.endswith(".py"):
            try:
                raw_content = repo.get_contents(file.filename, ref=pr.head.sha)
                full_text = base64.b64decode(raw_content.content).decode('utf-8')
            except Exception:
                full_text = ""
                
            patch_text = file.patch or "No patch available"
            
            print(f"Parsing {file.filename}...")
            parsed_data = analyze_python_file(full_text, patch_text)
            changed_python_files[file.filename] = parsed_data

    # Infrastructure Files Extraction
    infra_files = {}
    target_files = [
        "Dockerfile", "docker-compose.yml", "requirements.txt",
        "deployment.yaml", "service.yaml", "ingress.yaml",
        "k8s/deployment.yaml", "k8s/service.yaml", "kubernetes.yaml"
    ]
    
    for file_path in target_files:
        try:
            file_content = repo.get_contents(file_path, ref=pr.head.sha)
            decoded_text = base64.b64decode(file_content.content).decode('utf-8')
            infra_files[file_path] = decoded_text
        except Exception:
            pass

    # 4. Layer 2: Static Analysis Scanner
    print("Running Static Analysis Engine...")
    scanner = StaticAnalyzer()
    all_python_text = ""
    
    for filename, parsed_data in changed_python_files.items():
        if parsed_data.get("status") == "success":
            if "what_actually_changed_diff" in parsed_data:
                all_python_text += parsed_data["what_actually_changed_diff"]
                
            for func in parsed_data.get("impacted_functions", []):
                scanner.scan_python_code(filename, func["full_function_context"])
                
    for filename, yaml_text in infra_files.items():
        scanner.scan_infra_code(filename, yaml_text)
        
    scanner.check_global_repo_rules(all_python_text)
    static_analysis_results = scanner.get_results()
    print("Static Analysis complete! Passing to AI Agent...")

    # 5. Layer 3: LangGraph AI & Pinecone Vector DB
    findings_for_ai = static_analysis_results.get("details", [])
    ai_review_results = run_archguard_review(findings_for_ai, request.developer_context)

    print("Full Pipeline Complete!")


    return {
        "status": "success", 
        "pr_title": pr.title,
        "should_rollback": ai_review_results.get("should_rollback"),
        "overall_risk_score": ai_review_results.get("overall_risk"),
        "data": {
            "ai_review": ai_review_results,
            "static_analysis": static_analysis_results,
            "layer_1_parser": changed_python_files,
        }
    }


#enforce rollback ka endpoint
@app.post("/enforce-rollback")
async def enforce_rollback_endpoint(request: RollbackRequest):
    print(f"Initiating Rollback for: {request.pr_url}")
    
    try:
        parts = request.pr_url.rstrip('/').split('/')
        owner = parts[-4]
        repo_name = parts[-3]
        pr_number = int(parts[-1])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid GitHub PR URL.")

    g = Github(GITHUB_TOKEN)
    
    try:
        repo = g.get_repo(f"{owner}/{repo_name}")
        pr = repo.get_pull(pr_number)
        
        comment_body = f"""
# ArchGuard Automated Rollback
**Risk Score:** {request.risk_score} / 10.0

This Pull Request has been automatically closed by ArchGuard due to critical architectural or security vulnerabilities. 

**AI Diagnostics:**
{request.reason}

*Please resolve these issues locally and open a new Pull Request.*
"""
        pr.create_issue_comment(comment_body)
        pr.edit(state="closed")
        
        print(f"PR {pr_number} successfully closed.")
        return {"status": "success", "message": f"PR {pr_number} closed and commented."}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rollback. Error: {str(e)}")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)