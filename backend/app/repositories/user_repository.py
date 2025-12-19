from app.database.mongodb import get_database
from datetime import datetime
from app.models.user import UserInDB

class UserRepository:
    def __init__(self):
        self.collection_name = "users"


    async def find_by_github_id(self, github_id):
        db = get_database()

        user_data = await db[self.collection_name].find_one({"github_id": github_id})

        if user_data:
            # Convert ObjectId to string
            user_data["_id"] = str(user_data["_id"])
            return UserInDB(**user_data)
        return None

    async def create_or_update(self, user):

        db = get_database()

        users_collection = db[self.collection_name]


        result = await users_collection.update_one(
        {"github_id": user.github_id},
        {
            "$set": {
                "username": user.username,
                "avatar_url": user.avatar_url,
                "updated_at": datetime.utcnow()
            },
            "$setOnInsert": {
                "github_id": user.github_id,
                "email": None,
                "access_token": None,
                "repositories": [],
                "created_at": datetime.utcnow()
            }
        },
        upsert=True
        )

        # Return user ID
        if result.upserted_id:
            return str(result.upserted_id)
        else:
            user_doc = await self.find_by_github_id(user.github_id)
            return str(user_doc.id)
        
    async def add_repository(self, user_id, repo_id) -> bool :
        db = get_database()
        users_collection = db[self.collection_name]

        result = await users_collection.update_one(
            {"github_id": user_id},
            {"$addToSet": {"repositories": str(repo_id)}}  # $addToSet prevents duplicates
        )

        return result.modified_count>0

        
    
user_repo = UserRepository()