from fastapi import APIRouter, Request, HTTPException
from database import users_collection
from utils.jwt import verify_token

router = APIRouter()

@router.get("/stats")
async def get_stats(request: Request):
    auth = request.headers.get("Authorization")

    if not auth:
        return {"guest": True}

    try:
        token = auth.split(" ")[1]
        email = verify_token(token)

        user = await users_collection.find_one({"email": email})

        if not user:
            return {"guest": True}

        return {
            "guest": False,
            "history": user.get("history", [])
        }

    except:
        return {"guest": True}