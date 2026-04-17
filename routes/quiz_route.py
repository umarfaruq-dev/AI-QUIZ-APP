from fastapi import APIRouter, UploadFile, File, Request, HTTPException
import shutil
import os
from datetime import datetime, timezone

from services.quiz_service import create_quiz
from services.llm_service import generate_quiz
from services.pdf_service import extract_text
from services.chunk_service import chunk_text

from database import users_collection, ip_logs_collection
from utils.rate_limit import check_limits
from utils.jwt import verify_token

router = APIRouter()


# -----------------------------
# 🔹 Topic-based quiz
# -----------------------------
@router.get("/generate")
async def generate(topic: str, request: Request):

    try:
        topic = topic.strip()

        if len(topic) < 3:
            return {"error": "Topic too short"}

        # -----------------------------
        # 🌐 Get IP
        # -----------------------------
        user_ip = request.headers.get("x-forwarded-for")
        if user_ip:
            user_ip = user_ip.split(",")[0]
        else:
            user_ip = request.client.host

        # -----------------------------
        # 👤 Get user from JWT
        # -----------------------------
        user = None
        email = None

        auth = request.headers.get("Authorization")

        if auth:
            try:
                token = auth.split(" ")[1]
                email = verify_token(token)

                if email:
                    user = await users_collection.find_one({"email": email})

            except:
                user = None

        print("User:", user)

        # -----------------------------
        # 🚫 Rate limiting
        # -----------------------------
        now = await check_limits(user, user_ip, users_collection, ip_logs_collection)

        # -----------------------------
        # 🧠 Track attempt (marks = 0)
        # -----------------------------
        if user:
            await users_collection.update_one(
                {"email": email},
                {
                    "$push": {
                        "history": {
                            "marks": 0,
                            "time": now
                        }
                    }
                }
            )

        # -----------------------------
        # 🤖 Generate quiz
        # -----------------------------
        enriched_topic = f"Detailed topic: {topic}. Generate conceptual questions."
        quiz = await generate_quiz(enriched_topic)

        # -----------------------------
        # 💾 Save quiz (optional)
        # -----------------------------
        if user and isinstance(quiz, dict) and "error" not in quiz:
            await create_quiz({
                "type": "text_llm_topic",
                "quiz": quiz,
                "email": email,
                "created_at": now
            })

        # -----------------------------
        # 📡 Log IP
        # -----------------------------
        await ip_logs_collection.insert_one({
            "ip": user_ip,
            "time": now
        })

        return quiz

    except Exception as e:
        return {"error": str(e)}


# -----------------------------
# 📄 PDF-based quiz
# -----------------------------
@router.post("/generate-from-pdf")
async def generate_from_pdf(
    file: UploadFile = File(...),
    request: Request = None,
):
    file_path = f"temp_{file.filename}"

    try:
        # -----------------------------
        # 🌐 Get IP
        # -----------------------------
        user_ip = request.headers.get("x-forwarded-for")
        if user_ip:
            user_ip = user_ip.split(",")[0]
        else:
            user_ip = request.client.host

        # -----------------------------
        # 👤 Get user from JWT
        # -----------------------------
        user = None
        email = None

        auth = request.headers.get("Authorization")

        if auth:
            try:
                token = auth.split(" ")[1]
                email = verify_token(token)

                if email:
                    user = await users_collection.find_one({"email": email})

            except:
                user = None

        print("User:", user)

        # -----------------------------
        # 🚫 Rate limiting
        # -----------------------------
        now = await check_limits(user, user_ip, users_collection, ip_logs_collection)

        # -----------------------------
        # 🧠 Track attempt (marks = 0)
        # -----------------------------
        if user:
            await users_collection.update_one(
                {"email": email},
                {
                    "$push": {
                        "history": {
                            "marks": 0,
                            "time": now
                        }
                    }
                }
            )

        # -----------------------------
        # 💾 Save file
        # -----------------------------
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # -----------------------------
        # 📖 Extract + chunk
        # -----------------------------
        pages = extract_text(file_path)[:5]

        all_chunks = []
        for page in pages:
            all_chunks.extend(chunk_text(page))

        context = " ".join(all_chunks[:3])[:1200]

        # -----------------------------
        # 🤖 Generate quiz
        # -----------------------------
        quiz = await generate_quiz(context)

        # -----------------------------
        # 💾 Save quiz
        # -----------------------------
        if user and isinstance(quiz, dict) and "error" not in quiz:
            await create_quiz({
                "type": "text_llm_pdf",
                "quiz": quiz,
                "email": email,
                "created_at": now
            })

        # -----------------------------
        # 📡 Log IP
        # -----------------------------
        await ip_logs_collection.insert_one({
            "ip": user_ip,
            "time": now
        })

        return quiz

    except Exception as e:
        return {"error": str(e)}

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


# -----------------------------
# 🔥 Submit Quiz
# -----------------------------
@router.post("/submit-quiz")
async def submit_quiz(request: Request, score: int):

    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return {"message": "Guest mode - score not saved"}

    try:
        token = auth_header.split(" ")[1]
    except Exception:
        raise HTTPException(401, "Invalid token format")

    email = verify_token(token)

    if not email:
        raise HTTPException(401, "Invalid or expired token")

    # -----------------------------
    # 🔄 Update latest attempt (marks = 0 → score)
    # -----------------------------
    await users_collection.update_one(
        {
            "email": email,
            "history.marks": 0
        },
        {
            "$set": {
                "history.$.marks": score
            }
        }
    )

    return {"message": "Score saved successfully"}