"""
JWT token utilities
"""

# TODO: Implement JWT utilities
# - Create access tokens
# - Create refresh tokens
# - Verify tokens
# - Decode tokens
# - Token expiration handling

def create_access_token(data: dict, expires_delta: int = None) -> str:
    """Create JWT access token"""
    pass

def verify_token(token: str) -> dict:
    """Verify and decode JWT token"""
    pass

def get_current_user(token: str):
    """Get current user from token (dependency for FastAPI routes)"""
    pass
