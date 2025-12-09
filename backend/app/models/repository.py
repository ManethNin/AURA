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

from pydantic import BaseModel
from typing import List

class Repository(BaseModel):
    repo_id : str
    user_id : str
    repo_name : str
    commits :  str
    changes: List[str] = []

