"""
Agent Callback - Updates database with agent progress
"""
import asyncio
from typing import Optional, Dict
from app.repositories.change_repository import change_repo
from app.utils.logger import logger

class AgentCallback:
    """Callback that saves agent progress to database"""
    
    def __init__(self, change_id: str):
        self.change_id = change_id
    
    async def update_status(self, status: str, progress: int, message: str = ""):
        """Update status in database"""
        logger.info(f"[Agent {self.change_id}] {status}: {message} ({progress}%)")
        
        await change_repo.update_status(
            self.change_id,
            status,
            progress,
            message
        )
    
    async def save_result(self, diff: str, solution: str, modified_files: Optional[Dict[str, str]] = None):
        """Save final results to database"""
        logger.info(f"[Agent {self.change_id}] Completed! Diff size: {len(diff)} chars")
        if modified_files:
            logger.info(f"[Agent {self.change_id}] Modified files: {list(modified_files.keys())}")
        
        await change_repo.save_result(
            self.change_id,
            suggested_fix=solution,
            diff=diff,
            modified_files=modified_files
        )
    
    async def save_error(self, error: str):
        """Save error to database"""
        logger.error(f"[Agent {self.change_id}] Error: {error}")
        
        await change_repo.save_error(self.change_id, error)
