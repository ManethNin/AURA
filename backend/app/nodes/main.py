from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.memory.mongodb import connect_db, close_db
from app.nodes.routes import webhook, auth, repositories, users, changes, local_repos
from app.config.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()

app = FastAPI(lifespan=lifespan)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Backend running"}

# Conditionally include GitHub-specific routes
if not settings.LOCAL_MODE:
    app.include_router(webhook.router, prefix="/webhook", tags=["Webhook"])
    app.include_router(auth.router, prefix="/auth", tags=["Auth"])

app.include_router(repositories.router, prefix="/repositories", tags=["Repositories"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(changes.router, prefix="/changes", tags=["Changes"])

if settings.LOCAL_MODE:
    app.include_router(local_repos.router, prefix="/local", tags=["Local Repositories"])