"""
FastAPI dependencies for FinBot API.

Handles JWT token creation and validation.
The token carries the user's role — this is what
the chat endpoint uses for RBAC enforcement.
"""

import jwt
import logging
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.api.demo_users import DemoUser, DEMO_USERS

logger = logging.getLogger(__name__)

# Secret key for JWT signing
# In production: load from environment variable
JWT_SECRET    = "finbot-demo-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

security = HTTPBearer()


def create_token(user: DemoUser) -> str:
    """
    Create a JWT token containing the user's role and identity.
    This token is sent with every API request from the frontend.
    """
    payload = {
        "sub":        user.email,
        "role":       user.role,
        "name":       user.name,
        "department": user.department,
        "exp":        datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    FastAPI dependency — validates JWT token on protected routes.

    Usage:
        @router.post("/chat")
        def chat(current_user: dict = Depends(get_current_user)):
            role = current_user["role"]
    """
    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
        )
        return {
            "email":      payload["sub"],
            "role":       payload["role"],
            "name":       payload["name"],
            "department": payload["department"],
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token. Please log in again.",
        )