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

class ChangeStatus(str, Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    FIXED = "fixed"
    FAILED = "failed"

class Change(BaseModel):
    change_id: str
    repository_id: str
    commit_message: str
    files_changed: List[str]
    breaking_changes: Optional[List[Dict]] = []
    suggested_fixes: Optional[str] = None
    status: ChangeStatus = ChangeStatus.PENDING
    pr_url: Optional[str] = None  # PR created with fix
    
