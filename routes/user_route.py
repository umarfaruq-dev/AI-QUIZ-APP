from fastapi import APIRouter
from models.user_model import User
from services.user_service import create_user

router = APIRouter()

@router.post("/register")
async def register(user: User):
    return await create_user(user.dict())