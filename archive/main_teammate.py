from fastapi import FastAPI, HTTPException
import requests
import uvicorn
import subprocess

app = FastAPI()


@app.put("/merge_pr")
def merge_request(owner: str, repo: str, pull_number: int, github_token: str):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/merge"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_token}",
        "X-GitHub-Api-Version": "2026-03-10",
    }

    response = requests.put(url, headers=headers, json={"merge_method": "merge"})

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.json())

    json_response = response.json()
    return json_response["message"]


@app.get("/check_merge")
def check_pull_request(owner: str, repo: str, pull_number: int, github_token: str):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/merge"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_token}",
        "X-GitHub-Api-Version": "2026-03-10",
    }

    response = requests.get(url, headers=headers)
    status_code = response.status_code

    if status_code == 204:
        merged = True
        print("Your pull request has already been merged")
        return merged

    elif status_code == 404:
        merged = False
        print("Pull request either not found or not merged")
        return merged

    else:
        raise HTTPException(status_code=status_code, detail="Unexpected response checking merge status")


@app.post("/create_pull_request")
def create_pull_request(owner: str, repo: str, head: str, base: str, github_token: str, title: str, body: str):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_token}",
        "X-GitHub-Api-Version": "2026-03-10",
    }

    response = requests.post(
        url, headers=headers,
        json={"title": title, "head": head, "base": base, "body": body}
    )

    status_code = response.status_code

    if status_code == 201:
        print("A pull request has been created")
        return response.json()

    else:
        raise HTTPException(status_code=status_code, detail=response.json())


@app.post("/create_branch")
def create_branch(owner: str, repo: str, branch_name: str, sha: str, github_token: str):
    url = f"https://api.github.com/repos/{owner}/{repo}/git/refs"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_token}",
        "X-GitHub-Api-Version": "2026-03-10",
    }
    response = requests.post(
        url, headers=headers,
        json={"ref": f"refs/heads/{branch_name}", "sha": sha}
    )

    if response.status_code == 201:
        print("New branch created")
        return response.json()

    else:
        raise HTTPException(status_code=response.status_code, detail=response.json())


@app.patch("/close_request")
def close_pull_request(owner: str, repo: str, pull_number: int, github_token: str):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_token}",
        "X-GitHub-Api-Version": "2026-03-10",
    }
    body = {"state": "closed"}
    response = requests.patch(url, headers=headers, json=body)
    return response.json()


