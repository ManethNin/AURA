"""
LangGraph State Definition
Defines the shared state across all agent nodes
"""
from typing import TypedDict, List, Optional

class AgentState(TypedDict):
    """
    Shared state for the dependency repair agent workflow
    """
    # Input data
    commit_sha: str
    repository_name: str
    pom_content: str
    breaking_code: Optional[str]
    
    # Analysis results
    dependencies_with_issues: List[dict]
    error_details: Optional[str]
    
    # Repair attempts
    repair_attempts: int
    max_attempts: int
    
    # Generated fixes
    suggested_fix: Optional[str]
    fix_explanation: Optional[str]
    
    # Status
    status: str  # analyzing/repairing/fixed/failed
    error_message: Optional[str]

# TODO: Adjust fields based on your exact workflow needs
