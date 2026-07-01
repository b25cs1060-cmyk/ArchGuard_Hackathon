from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from github import Github
import uvicorn
import base64
import os
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
    allow_origins=[
        "https://arch-guard-hackathon.vercel.app",
        "http://localhost:5173", 
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN not found! Please check your .env file.")


class PRRequest(BaseModel):
    pr_url: str

class AnswerSubmitRequest(BaseModel):
    pr_url: str
    developer_answers: str

class RollbackRequest(BaseModel):
    pr_url: str
    risk_score: float
    reason: str



def merge_request(owner: str, repo: str, pull_number: int, github_token: str):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/merge"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_token}",
        "X-GitHub-Api-Version": "2026-03-10"
    }
    response = requests.put(url, headers=headers, json={"merge_method": "merge"})
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.json())
    return response.json()["message"]


def check_pull_request(owner: str, repo: str, pull_number: int, github_token: str):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/merge"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_token}",
        "X-GitHub-Api-Version": "2026-03-10"
    }
    response = requests.get(url, headers=headers)
    return response.status_code == 204  # True if merged


def create_pull_request(owner: str, repo: str, head: str, base: str,
                         github_token: str, title: str, body: str):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_token}",
        "X-GitHub-Api-Version": "2026-03-10"
    }
    response = requests.post(url, headers=headers,
                              json={"title": title, "head": head, "base": base, "body": body})
    if response.status_code != 201:
        raise HTTPException(status_code=response.status_code, detail=response.json())
    return response.json()


def create_branch(owner: str, repo: str, branch_name: str, sha: str, github_token: str):
    url = f"https://api.github.com/repos/{owner}/{repo}/git/refs"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_token}",
        "X-GitHub-Api-Version": "2026-03-10"
    }
    response = requests.post(url, headers=headers,
                              json={"ref": f"refs/heads/{branch_name}", "sha": sha})
    if response.status_code != 201:
        raise HTTPException(status_code=response.status_code, detail=response.json())
    return response.json()


def close_pull_request(owner: str, repo: str, pull_number: int,
                        github_token: str, risk_score: float, reason: str):
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


def get_pre_merge_sha(owner: str, repo: str, pull_number: int, github_token: str) -> str:
    """
    Gets the exact SHA of main right before this specific PR was merged.
    Uses the PR's own base SHA — the most reliable way to find the safe
    stable commit, regardless of other recent commits on the repo.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_token}",
        "X-GitHub-Api-Version": "2026-03-10"
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Could not fetch PR details to determine stable SHA: {response.json()}"
        )
    pr_data = response.json()
    return pr_data["base"]["sha"]


def handle_post_merge(owner: str, repo: str, pull_number: int,
                       github_token: str, base_branch: str = "main"):
    """
    1. Gets the exact commit SHA that main was at BEFORE the merge.
    2. Gets the current HEAD of main.
    3. Creates a new branch off CURRENT main.
    4. Creates a new commit that forces the file tree to look exactly like the old stable state.
    5. Opens a PR to merge this revert commit safely into main.
    """
    import time
    
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_token}",
        "X-GitHub-Api-Version": "2026-03-10"
    }

    stable_sha = get_pre_merge_sha(owner, repo, pull_number, github_token)

    url_main = f"https://api.github.com/repos/{owner}/{repo}/git/ref/heads/{base_branch}"
    res_main = requests.get(url_main, headers=headers).json()
    
    if "object" not in res_main:
        raise HTTPException(status_code=500, detail="Failed to fetch current main HEAD.")
    main_sha = res_main["object"]["sha"]

    branch_name = f"archguard-revert-{int(time.time())}"
    create_branch(owner, repo, branch_name, main_sha, github_token)

    url_stable_commit = f"https://api.github.com/repos/{owner}/{repo}/git/commits/{stable_sha}"
    res_stable = requests.get(url_stable_commit, headers=headers).json()
    stable_tree_sha = res_stable["tree"]["sha"]

    url_create_commit = f"https://api.github.com/repos/{owner}/{repo}/git/commits"
    commit_payload = {
        "message": f"Automated Rollback: Reverting to stable state {stable_sha[:7]}",
        "tree": stable_tree_sha,
        "parents": [main_sha]
    }
    res_new_commit = requests.post(url_create_commit, headers=headers, json=commit_payload).json()
    new_commit_sha = res_new_commit["sha"]

    url_update_ref = f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{branch_name}"
    requests.patch(url_update_ref, headers=headers, json={"sha": new_commit_sha})

    return create_pull_request(
        owner, repo, branch_name, base_branch, github_token,
        title=f"Automated Rollback: Critical Risk Detected in PR #{pull_number}",
        body=f"ArchGuard detected severe architectural risks after this code was merged.\n\n"
             f"This PR safely reverts the codebase to the last known stable state (`{stable_sha[:7]}`). "
             f"Review and merge immediately to contain the blast radius."
    )


def take_decision(should_rollback: bool, owner: str, repo: str, pull_number: int,
                   github_token: str, risk_score: float, reason: str, base_branch: str = "main"):
    if should_rollback:
        is_merged = check_pull_request(owner, repo, pull_number, github_token)

        if is_merged:
            # PR already merged → create rollback branch + open PR to revert main
            return handle_post_merge(owner, repo, pull_number, github_token, base_branch)
        else:
            # PR not yet merged → close it with a comment explaining why
            return close_pull_request(owner, repo, pull_number, github_token, risk_score, reason)
    else:
        # Risk is acceptable → merge the PR
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