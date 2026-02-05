from fastapi import FastAPI, Header
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from app.database.mongodb import connect_db, close_db
from typing import Optional, List, Dict, Any
from app.api.routes import webhook, auth, repositories, users, changes, local_repos
from app.core.config import settings


app = FastAPI()



# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await connect_db()

@app.on_event("shutdown")
async def shutdown():
    await close_db()

@app.get("/")
def root():
    return {"message": "Backend running"}


# Include routers
# Conditionally include GitHub-specific routes
if not settings.LOCAL_MODE:
    app.include_router(webhook.router, prefix="/webhook", tags=["Webhook"])
    app.include_router(auth.router, prefix="/auth", tags=["Auth"])

# Always include these routes
app.include_router(repositories.router, prefix="/repositories", tags=["Repositories"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(changes.router, prefix="/changes", tags=["Changes"])

# Local mode routes
if settings.LOCAL_MODE:
    app.include_router(local_repos.router, prefix="/local", tags=["Local Repositories"])
