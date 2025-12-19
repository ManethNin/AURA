"""
User MongoDB model
"""

# TODO: Define User model
# - _id
# - github_username
# - github_id
# - email
# - access_token (encrypted)
# - installed_repos []
# - created_at
# - updated_at

"""
User MongoDB model
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class User(BaseModel):
    github_id: str  # GitHub user ID (unique)
    username: str  # GitHub username
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    access_token: Optional[str] = None  # GitHub OAuth token (will add later)
    repositories: List[str] = []  # List of repository IDs
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class UserInDB(User):
    """User model as stored in database (with _id)"""
    id: Optional[str] = Field(None, alias="_id")
    
    class Config:
        populate_by_name = True