"""
Change/Suggestion MongoDB model
Stores detected dependency issues and suggested fixes
"""

# TODO: Define Change model
# - _id
# - repository_id (reference)
# - commit_sha
# - commit_message
# - detected_at
# - breaking_dependencies [] (list of dependencies with issues)
# - original_code
# - suggested_fix
# - fix_status (pending/in_progress/fixed/failed)
# - pull_request_url (if PR created)
# - error_message (if repair failed)
# - created_at
# - updated_at

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum

class FixStatus(str, Enum):
    PENDING = "pending"
    CLONING = "cloning"
    PREPARING = "preparing"
    ANALYZING = "analyzing"
    FIXING = "fixing"
    VALIDATING = "validating"
    FIXED = "fixed"
    FAILED = "failed"

class Change(BaseModel):
    repository_id: str
    commit_sha: str
    commit_message: str
    pom_content: Optional[str] = None
    
    # Agent results
    breaking_changes: Optional[str] = None
    suggested_fix: Optional[str] = None
    diff: Optional[str] = None
    
    # Status tracking
    status: FixStatus = FixStatus.PENDING
    progress: int = 0
    status_message: Optional[str] = None
    error_message: Optional[str] = None
    
    # Pull Request
    pull_request_url: Optional[str] = None
    
    # Execution details
    agent_output_path: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ChangeInDB(Change):
    """Change model as stored in database (with _id)"""
    id: Optional[str] = Field(None, alias="_id")
    
    class Config:
        populate_by_name = True


