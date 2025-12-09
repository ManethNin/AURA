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

from pydantic import BaseModel
from typing import Optional, List


class User(BaseModel):
    user_id : str
    user_name :  str
    github_username : str
    github_id : str
    email : str
    access_token : str
    repositories : List[str] = []