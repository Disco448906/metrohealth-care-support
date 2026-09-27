from fastapi import APIRouter, HTTPException, Depends, status, Header
from typing import Optional
from datetime import datetime
from backend.schemas.schemas import UserRegister, UserLogin, TokenResponse, UserResponse
from backend.utils.security import hash_password, verify_password, create_access_token, decode_access_token
from backend.database.connection import get_db

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header token."
        )
    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token."
        )

    db = get_db()
    # Use the stable account id when present so an admin correction to a
    # patient's email does not invalidate an already issued session token.
    user = db["users"].find_one({"id": payload["id"]}) if payload.get("id") else None
    if not user:
        user = db["users"].find_one({"email": payload["sub"]})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found."
        )

    user_id = str(user.get("id") or user.get("_id") or "")
    user["id"] = user_id
    user.pop("password", None)
    return user

def get_current_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to access this resource."
        )
    return user

def get_current_doctor(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "doctor" or not user.get("doctor_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor privileges are required to access this resource."
        )
    return user

@router.post("/register", response_model=TokenResponse)
def register(user_data: UserRegister):
    db = get_db()
    existing_user = db["users"].find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    user_id = f"usr_{int(datetime.utcnow().timestamp())}"
    hashed_pwd = hash_password(user_data.password)

    user_doc = {
        "id": user_id,
        "name": user_data.name,
        "email": user_data.email,
        "password": hashed_pwd,
        # Public registration is patient-only. Staff accounts are provisioned by an administrator.
        "role": "customer",
        "phone": user_data.phone or "+1 (555) 019-2831",
        "created_at": datetime.utcnow().isoformat()
    }

    db["users"].insert_one(user_doc)

    token = create_access_token({"sub": user_data.email, "role": user_doc["role"], "id": user_id})

    user_payload = {
        "id": user_id,
        "name": user_doc["name"],
        "email": user_doc["email"],
        "role": user_doc["role"],
        "phone": user_doc["phone"],
        "created_at": user_doc["created_at"]
    }

    return {"access_token": token, "token_type": "bearer", "user": user_payload}

@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin):
    db = get_db()
    user = db["users"].find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )
    if user.get("account_locked"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This patient account is locked. Please contact support.",
        )

    user_id = str(user.get("id") or user.get("_id") or "")
    token = create_access_token({"sub": user["email"], "role": user.get("role", "customer"), "id": user_id})

    user_payload = {
        "id": user_id,
        "name": user["name"],
        "email": user["email"],
        "role": user.get("role", "customer"),
        "phone": user.get("phone", "+1 (555) 019-2831"),
        "created_at": user.get("created_at", datetime.utcnow().isoformat())
    }

    return {"access_token": token, "token_type": "bearer", "user": user_payload}

@router.get("/me", response_model=UserResponse)
def get_profile(current_user: dict = Depends(get_current_user)):
    return current_user
