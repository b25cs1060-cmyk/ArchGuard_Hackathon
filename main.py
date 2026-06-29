from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from github import Github
import uvicorn
import base64
import os
from dotenv import load_dotenv

from parser import analyze_python_file
from analyzer import StaticAnalyzer

load_dotenv()

app = FastAPI(title="ArchGuard API")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN not found! Please check your .env file.")

class PRRequest(BaseModel):
    pr_url: str

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


    changed_python_files = {}
    for file in pr.get_files():
        if file.filename.endswith(".py"):
            try:
                raw_content = repo.get_contents(file.filename, ref=pr.head.sha)
                full_text = base64.b64decode(raw_content.content).decode('utf-8')
            except Exception:
                full_text = ""
                
            patch_text = file.patch or "No patch available"
            
            # Parsing via Layer 1
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
    print("Analysis complete!")


    return {
        "status": "success", 
        "pr_title": pr.title,
        "data": {
            "python_files": changed_python_files,
            "infra_files": infra_files
        },
        "layer_2_analysis": static_analysis_results
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)