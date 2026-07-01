from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from github import Github
import uvicorn
import base64
import os
import subprocess
import requests
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from parser import analyze_python_file
from analyzer import StaticAnalyzer
from ai_agent import start_review_and_ask_questions, resume_review_with_answers  

load_dotenv()

app = FastAPI(title="ArchGuard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN not found! Please check your .env file.")

REPO_PATH = os.getcwd()


class PRRequest(BaseModel):
    pr_url: str

class AnswerSubmitRequest(BaseModel):
    pr_url: str
    developer_answers: str

class RollbackRequest(BaseModel):
    pr_url: str
    risk_score: float
    reason: str

#github helper fns

def merge_request(owner: str, repo: str, pull_number: int, github_token: str):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/merge"
    headers = {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {github_token}", "X-GitHub-Api-Version": "2026-03-10"}
    response = requests.put(url, headers=headers, json={"merge_method": "merge"})
    if response.status_code != 200: raise HTTPException(status_code=response.status_code, detail=response.json())
    return response.json()["message"]

def check_pull_request(owner: str, repo: str, pull_number: int, github_token: str):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/merge"
    headers = {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {github_token}", "X-GitHub-Api-Version": "2026-03-10"}
    response = requests.get(url, headers=headers)
    return response.status_code == 204 # True if merged

def create_pull_request(owner: str, repo: str, head: str, base: str, github_token: str, title: str, body: str):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    headers = {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {github_token}", "X-GitHub-Api-Version": "2026-03-10"}
    response = requests.post(url, headers=headers, json={"title": title, "head": head, "base": base, "body": body})
    if response.status_code != 201: raise HTTPException(status_code=response.status_code, detail=response.json())
    return response.json()

def create_branch(owner: str, repo: str, branch_name: str, sha: str, github_token: str):
    url = f"https://api.github.com/repos/{owner}/{repo}/git/refs"
    headers = {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {github_token}", "X-GitHub-Api-Version": "2026-03-10"}
    response = requests.post(url, headers=headers, json={"ref": f"refs/heads/{branch_name}", "sha": sha})
    return response.json()

def close_pull_request(owner, repo, pull_number, github_token, risk_score, reason):
    g = Github(github_token)
    repo_obj = g.get_repo(f"{owner}/{repo}")
    pr = repo_obj.get_pull(pull_number)
    

    comment_body = f"""
# ArchGuard Automated Rollback
**Risk Score:** {risk_score} / 10.0

This Pull Request has been automatically closed by ArchGuard due to critical architectural or security vulnerabilities. 

**AI Diagnostics:**
{reason}

*Please resolve these issues locally and open a new Pull Request.*
"""
    pr.create_issue_comment(comment_body)
    pr.edit(state="closed")
    print(f"PR {pull_number} successfully closed and commented.")
    return {"message": "PR closed and commented"}


def handle_post_merge(owner, repo, repo_path, github_token, old_ref, base_branch):
    stable_sha = subprocess.run(["git", "rev-parse", old_ref], cwd=repo_path, check=True, capture_output=True, text=True).stdout.strip()
    branch_name = f"rollback-to-stable-{stable_sha[:7]}"
    create_branch(owner, repo, branch_name, stable_sha, github_token)
    return create_pull_request(owner, repo, branch_name, base_branch, github_token, "Automated Rollback", f"Reverting to {stable_sha[:7]}")

def take_decision(should_rollback, owner, repo, pull_number, github_token, risk_score, reason, base_branch="main"):
    if should_rollback:
        is_merged = check_pull_request(owner, repo, pull_number, github_token)
        
        if is_merged:

            return handle_post_merge(owner, repo, REPO_PATH, github_token, "HEAD~1", base_branch)
        else:

            return close_pull_request(owner, repo, pull_number, github_token, risk_score, reason)
    else:
        return merge_request(owner, repo, pull_number, github_token)
    


@app.post("/analyze-pr")
async def analyze_pr_endpoint(request: PRRequest):
    print(f"Received URL: {request.pr_url}")
    

    try:
        parts = request.pr_url.rstrip('/').split('/')
        owner = parts[-4]
        repo_name = parts[-3]
        pr_number = str(parts[-1])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid GitHub PR URL format.")


    g = Github(GITHUB_TOKEN)
    try:
        repo = g.get_repo(f"{owner}/{repo_name}")
        pr = repo.get_pull(int(pr_number))
        print(f"Successfully fetched PR: '{pr.title}'")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Could not fetch PR. Error: {str(e)}")

    print("Extracting and Parsing files...")


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

    # 5. Layer 3: Start AI Agent and Pause for Questions
    findings_for_ai = static_analysis_results.get("details", [])
    ai_paused_state = start_review_and_ask_questions(findings_for_ai, thread_id=pr_number)

    return {
        "status": "pending_human_input", 
        "pr_title": pr.title,
        "questions_for_developer": ai_paused_state.get("questions", []),
        "data": {
            "static_analysis": static_analysis_results,
            "layer_1_parser": changed_python_files,
        }
    }



@app.post("/submit-answers")
async def submit_answers_endpoint(request: AnswerSubmitRequest):

    try:

        clean_url = request.pr_url.rstrip('/')
        parts = clean_url.split('/')
        pr_number = parts[-1]
        
        print(f"DEBUG: Extracted PR Number: {pr_number}")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid GitHub PR URL format.")
        

    final_ai_results = resume_review_with_answers(pr_number, request.developer_answers)

    print("Full Pipeline Complete!")

    return {
        "status": "success", 
        "should_rollback": final_ai_results.get("should_rollback"),
        "overall_risk_score": final_ai_results.get("overall_risk"),
        "data": {
            "ai_review": final_ai_results
        }
    }



@app.post("/enforce-rollback")
async def enforce_rollback_endpoint(request: RollbackRequest):
    parts = request.pr_url.rstrip('/').split('/')
    owner, repo, pull_number = parts[-4], parts[-3], int(parts[-1])

    result = take_decision(
        should_rollback=True, 
        owner=owner, 
        repo=repo, 
        pull_number=pull_number, 
        github_token=GITHUB_TOKEN,
        risk_score=request.risk_score,
        reason=request.reason
    )
    
    return {"status": "success", "action_taken": result}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)