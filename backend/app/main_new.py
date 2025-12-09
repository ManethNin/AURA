from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import webhook, auth, repositories, users

# TODO: Import database connection
# from app.database.mongodb import connect_db, close_db

app = FastAPI(title=settings.APP_NAME)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(webhook.router, prefix="/webhook", tags=["webhook"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(repositories.router, prefix="/repositories", tags=["repositories"])
app.include_router(users.router, prefix="/users", tags=["users"])

@app.get("/")
def root():
    return {"message": "AURA Backend - Automated Dependency Repair System"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# TODO: Add startup and shutdown events
# @app.on_event("startup")
# async def startup_event():
#     await connect_db()

# @app.on_event("shutdown")
# async def shutdown_event():
#     await close_db()
