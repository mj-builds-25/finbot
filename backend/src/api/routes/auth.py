"""
Authentication routes for FinBot API.

POST /auth/login  — validate credentials, return JWT token
GET  /auth/me     — return current user info from token
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from src.api.demo_users import authenticate, DEMO_USERS
from src.api.dependencies import create_token, get_current_user
from src.retrieval.rbac import get_accessible_collections

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email:    str
    password: str


class LoginResponse(BaseModel):
    token:       str
    email:       str
    name:        str
    role:        str
    department:  str
    collections: list[str]


class UserResponse(BaseModel):
    email:       str
    name:        str
    role:        str
    department:  str
    collections: list[str]


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
    """
    Validate credentials and return a JWT token.
    The token encodes the user's role for RBAC enforcement.
    """
    user = authenticate(request.email, request.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = create_token(user)
    collections = get_accessible_collections(user.role)

    return LoginResponse(
        token=token,
        email=user.email,
        name=user.name,
        role=user.role,
        department=user.department,
        collections=collections,
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: dict = Depends(get_current_user)):
    """Return current user info from their JWT token."""
    collections = get_accessible_collections(current_user["role"])
    return UserResponse(
        email=current_user["email"],
        name=current_user["name"],
        role=current_user["role"],
        department=current_user["department"],
        collections=collections,
    )


@router.get("/demo-users")
def get_demo_users():
    """
    Return list of demo users for the login screen.
    Only returns non-sensitive info — no passwords.
    """
    return [
        {
            "email":      user.email,
            "name":       user.name,
            "role":       user.role,
            "department": user.department,
        }
        for user in DEMO_USERS.values()
    ]