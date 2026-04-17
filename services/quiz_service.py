from database import quiz_collection

async def create_quiz(quiz_data):
    await quiz_collection.insert_one(quiz_data)
    return {"message": "Quiz stored successfully"}