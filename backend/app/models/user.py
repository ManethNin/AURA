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

from pydantic import BaseModel, Field
from typing import Optional, List


class User(BaseModel):
    github_id : str
    username :  str
    github_username : str
    github_id : str
    email : str
    access_token : str
    repositories : List[str] = []

class UserInDB(User):
    """User model as stored in database (with _id)"""
    id: Optional[str] = Field(None, alias="_id")
    
    class Config:
        populate_by_name = True