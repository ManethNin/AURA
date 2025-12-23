from fastapi import FastAPI, Header
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from app.database.mongodb import connect_db, close_db
from typing import Optional, List, Dict, Any
from app.api.routes import webhook, auth, repositories, users, changes


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
app.include_router(webhook.router, prefix="/webhook", tags=["Webhook"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(repositories.router, prefix="/repositories", tags=["Repositories"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(changes.router, prefix="/changes", tags=["Changes"])
