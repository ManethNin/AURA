"""
Repository MongoDB model
"""

# TODO: Define Repository model
# - _id
# - user_id (reference)
# - github_repo_id
# - full_name (owner/repo)
# - installation_id
# - is_active
# - last_commit_sha
# - created_at
# - updated_at

"""
Repository MongoDB model
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class Repository(BaseModel):
    github_repo_id: str  # GitHub repository ID (unique)
    name: str  # Repository name (e.g., "AURA")
    full_name: str  # Full name (e.g., "ManethNin/AURA")
    owner: str  # Repository owner username
    owner_id: str  # GitHub owner ID
    installation_id: Optional[int] = None  # GitHub App installation ID
    is_active: bool = True
    last_commit_sha: Optional[str] = None
    last_pom_change: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class RepositoryInDB(Repository):
    """Repository model as stored in database (with _id)"""
    id: Optional[str] = Field(None, alias="_id")
    
    class Config:
        populate_by_name = True
