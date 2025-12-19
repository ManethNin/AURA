from datetime import datetime
from app.database.mongodb import get_database
from app.models.repository import RepositoryInDB

class RepositoryRepository:
    def __init__(self):
        self.collection_name = "repositories"

    async def find_by_githubid(self, github_repo_id):
        db = get_database()
        repo_collection = db[self.collection_name]

        repo_data = await repo_collection.find_one({"github_repo_id": github_repo_id})

        if repo_data:
            # Convert ObjectId to string
            repo_data["_id"] = str(repo_data["_id"])
            return RepositoryInDB(**repo_data)
        return None

    async def create_or_update(self, repository):

        db = get_database()
        repo_collection = db[self.collection_name]

        result = await repo_collection.update_one(
        {"github_repo_id": repository.github_repo_id},
        {
            "$set": {
                "name": repository.name,
                "full_name": repository.full_name,
                "owner": repository.owner,
                "owner_id": repository.owner_id,
                "installation_id": repository.installation_id,
                "last_commit_sha": repository.last_commit_sha,
                "last_pom_change": repository.last_pom_change,
                "updated_at": datetime.utcnow()
            },
            "$setOnInsert": {
                "github_repo_id": repository.github_repo_id,
                "is_active": True,
                "created_at": datetime.utcnow()
            }
        },
        upsert=True
        )
        
        if result.upserted_id:
            return str(result.upserted_id)
        repo_doc = await self.find_by_githubid(repository.github_repo_id)

        return str(repo_doc.id)

        
repository_repo = RepositoryRepository()


    

