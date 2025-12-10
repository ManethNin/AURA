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

from pydantic import BaseModel, Field
from typing import List, Optional

class Repository(BaseModel):
    repo_id : str
    user_id : str
    repo_name : str
    commits :  str
    changes: List[str] = []

class RepRepositoryInDB(Repository):
    """Repository model as stored in database (with _id)"""
    id: Optional[str] = Field(None, alias="_id")
    
    class Config:
        populate_by_name = True

