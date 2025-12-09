"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# GitHub webhook schemas
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
    ref: str
    repository: Repository
    commits: List[Commit]
    head_commit: Optional[Commit] = None

# TODO: Add more schemas
# - User schemas (UserCreate, UserResponse, UserUpdate)
# - Repository schemas (RepositoryResponse, RepositoryList)
# - Change schemas (ChangeResponse, ChangeCreate, SuggestionResponse)
# - Auth schemas (LoginRequest, TokenResponse)
# - Pull Request schemas (PRCreateRequest, PRResponse)
