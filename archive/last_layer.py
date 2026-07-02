import subprocess
from main import (
    merge_request,
    check_pull_request,
    create_pull_request,
    create_branch,
    close_pull_request,

)

def handle_post_merge(owner: str, repo: str, repo_path: str, should_rollback: bool,
                                github_token: str, old_ref: str, base_branch: str):
    if not should_rollback:
        return {"rollback_triggered": False, "message": "should_rollback is False, no action taken."}

    stable_sha = subprocess.run(
        ["git", "rev-parse", old_ref], cwd=repo_path, check=True,
        capture_output=True, text=True
    ).stdout.strip()

    branch_name = f"rollback-to-stable-{stable_sha[:7]}"

    create_branch(owner, repo, branch_name, stable_sha, github_token)

    pr_response = create_pull_request(
        owner, repo, branch_name, base_branch, github_token,
        title=" Automated Rollback",
        body=f"This PR reverts {base_branch} to commit {stable_sha[:7]} (last known-stable)."
    )

    return {
        "rollback_triggered": True,
        "branch_created": branch_name,
        "pr_number": pr_response.get("number"),
        "pr_url": pr_response.get("html_url")
    }


def take_decision(should_rollback: bool, owner: str, repo: str, repo_path: str, pull_number: int,
                   old_ref: str, base_branch: str, github_token: str):
    if should_rollback == True:
        merged = check_pull_request(owner, repo, pull_number, github_token)
        if merged == True:
            handle_post_merge(owner, repo, repo_path, True, github_token, old_ref, base_branch)
        else:
            close_pull_request(owner, repo, pull_number, github_token)

    else:
        merge_request(owner, repo, pull_number, github_token)