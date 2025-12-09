from fastapi import FastAPI, Header
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

app = FastAPI()

class Commit(BaseModel):
    id: str
    message: str
    author: Dict[str, Any]
    added: List[str] = []
    modified: List[str] = []
    removed: List[str] = []

class Repository(BaseModel):
    name: str
    full_name: str
    
class WebhookPayload(BaseModel):
    ref: str  # branch reference
    repository: Repository
    commits: List[Commit]
    head_commit: Optional[Commit] = None

@app.get("/")
def root():
    return {"message": "Backend running"}

@app.post("/webhook")
async def github_webhook(
    payload: WebhookPayload,
    x_github_event: Optional[str] = Header(None)
):
    # Only process push events
    if x_github_event != "push":
        return {"message": "Ignored: not a push event by AURA"}
    
    pom_commits = []
    
    for commit in payload.commits:
        # Check if pom.xml was added, modified, or removed
        all_files = commit.added + commit.modified + commit.removed
        if "pom.xml" in all_files or any("pom.xml" in f for f in all_files):
            pom_commits.append({
                "id": commit.id,
                "message": commit.message,
                "files": all_files
            })
    
    if pom_commits:
        return {
            "message": "pom.xml changes detected by AURA",
            "repository": payload.repository.full_name,
            "branch": payload.ref,
            "commits": pom_commits
        }
    
    return {"message": "No pom.xml changes"}