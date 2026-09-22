from fastapi import APIRouter, HTTPException
from database.mongodb import db
from models.user import UserLogin
from utils.security import verify_password
from utils.jwt import create_access_token

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)


@router.post("/login")
async def login(user: UserLogin):

    # Find user in MongoDB
    existing_user = await db.users.find_one({
        "username": user.username
    })

    if not existing_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    # Verify password against bcrypt hash
    password_valid = verify_password(
        user.password,
        existing_user["password_hash"]
    )

    if not password_valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    # Create JWT
    token = create_access_token({
        "sub": str(existing_user["_id"]),
        "username": existing_user["username"],
        "role": existing_user["role"]
    })

    return {
        "success": True,
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "username": existing_user["username"],
            "email": existing_user["email"],
            "role": existing_user["role"]
        }
    }