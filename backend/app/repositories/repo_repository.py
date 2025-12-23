from datetime import datetime
from app.database.mongodb import get_database
from app.models.repository import RepositoryInDB
from app.repositories.change_repository import change_repo
from bson import ObjectId

class RepositoryRepository:
    def __init__(self):
        self.collection_name = "repositories"

    async def find_all_by_owner_id(self, owner_id):
        db = get_database()
        repo_collection = db[self.collection_name]

        repos = await repo_collection.find({"owner_id":owner_id}).to_list(None)

        for repo in repos:
            repo["_id"] = str(repo["_id"])

        return repos



    async def find_by_id(self, id):
        db = get_database()
        repo_collection = db[self.collection_name]

        repo_data = await repo_collection.find_one({"_id": ObjectId(id)})

        if repo_data:
            # Convert ObjectId to string
            repo_data["_id"] = str(repo_data["_id"])
            return RepositoryInDB(**repo_data)
        return None
    
    async def find_by_github_id(self, github_id):
        db = get_database()
        repo_collection = db[self.collection_name]

        repo_data = await repo_collection.find_one({"github_repo_id": github_id})

        if repo_data:
            # Convert ObjectId to string
            repo_data["_id"] = str(repo_data["_id"])
            return RepositoryInDB(**repo_data)
        return None
    
    async def delete_by_id(self, id):
        db = get_database()
        repo_collection = db[self.collection_name]

        repo_data = await repo_collection.delete_one({"_id": ObjectId(id)})
        await change_repo.delete_by_repo_id(id)
        
        if repo_data:
            # Convert ObjectId to string
            repo_data["_id"] = str(repo_data["_id"])
            return repo_data["github_repo_id"]
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
        repo_doc = await self.find_by_github_id(repository.github_repo_id)

        return str(repo_doc.id)

        
repository_repo = RepositoryRepository()


    

