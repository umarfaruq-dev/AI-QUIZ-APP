from database import users_collection

async def create_user(user_data):
    existing = await users_collection.find_one({"email": user_data["email"]})

    if existing:
        return {"error": "User already exists"}

    await users_collection.insert_one({
        "username": user_data["username"],
        "email": user_data["email"],
        "history": []
    })

    return {"message": "User created successfully"}