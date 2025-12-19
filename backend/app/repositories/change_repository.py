"""
Change Repository - Database operations for changes
"""
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from app.database.mongodb import get_database
from app.models.change import Change, ChangeInDB, FixStatus

class ChangeRepository:
    """Handles all change database operations"""
    
    def __init__(self):
        self.collection_name = "changes"
    
    async def create(self, change: Change) -> str:
        """Create new change record"""
        db = get_database()
        
        result = await db[self.collection_name].insert_one(change.dict())
        return str(result.inserted_id)
    
    async def find_by_id(self, change_id: str) -> Optional[ChangeInDB]:
        """Find change by ID"""
        db = get_database()
        
        change_data = await db[self.collection_name].find_one(
            {"_id": ObjectId(change_id)}
        )
        
        if change_data:
            # Convert ObjectId to string
            change_data["_id"] = str(change_data["_id"])
            return ChangeInDB(**change_data)
        return None
    
    async def find_by_repository(self, repository_id: str) -> List[ChangeInDB]:
        """Find all changes for a repository"""
        db = get_database()
        
        cursor = db[self.collection_name].find(
            {"repository_id": repository_id}
        ).sort("created_at", -1)
        
        changes = await cursor.to_list(length=100)
        # Convert ObjectId to string for each change
        for change in changes:
            change["_id"] = str(change["_id"])
        return [ChangeInDB(**change) for change in changes]
    
    async def update_status(
        self, 
        change_id: str, 
        status: str, 
        progress: int = 0,
        message: str = "",
        pom_content: Optional[str] = None
    ):
        """Update change status"""
        db = get_database()
        
        update_data = {
            "status": status,
            "progress": progress,
            "status_message": message,
            "updated_at": datetime.utcnow()
        }
        
        if pom_content is not None:
            update_data["pom_content"] = pom_content
        
        await db[self.collection_name].update_one(
            {"_id": ObjectId(change_id)},
            {"$set": update_data}
        )
    
    async def save_result(
        self,
        change_id: str,
        suggested_fix: str,
        diff: str,
        breaking_changes: Optional[str] = None,
        output_path: Optional[str] = None
    ):
        """Save agent results"""
        db = get_database()
        
        await db[self.collection_name].update_one(
            {"_id": ObjectId(change_id)},
            {
                "$set": {
                    "suggested_fix": suggested_fix,
                    "diff": diff,
                    "breaking_changes": breaking_changes,
                    "agent_output_path": output_path,
                    "status": "fixed",
                    "progress": 100,
                    "updated_at": datetime.utcnow()
                }
            }
        )
    
    async def save_error(self, change_id: str, error_message: str):
        """Save error"""
        db = get_database()
        
        await db[self.collection_name].update_one(
            {"_id": ObjectId(change_id)},
            {
                "$set": {
                    "status": "failed",
                    "error_message": error_message,
                    "updated_at": datetime.utcnow()
                }
            }
        )

# Singleton instance
change_repo = ChangeRepository()
