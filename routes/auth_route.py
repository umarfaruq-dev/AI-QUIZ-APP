import random
import os
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

from database import users_collection
from utils.jwt import create_token

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

load_dotenv()

router = APIRouter()

# -----------------------------
#  Email Config
# -----------------------------
conf = ConnectionConfig(
    MAIL_USERNAME="uf783413@gmail.com",
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM="uf783413@gmail.com",
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False
)

async def send_email(to_email: str, subject: str, body: str):
    message = MessageSchema(
        subject=subject,
        recipients=[to_email],
        body=body,
        subtype="plain"
    )
    fm = FastMail(conf)
    await fm.send_message(message)

# -----------------------------
#  OTP Store
# -----------------------------
otp_store = {}

# -----------------------------
#  Models
# -----------------------------
class EmailRequest(BaseModel):
    name: str | None = None
    email: str

class VerifyOTP(BaseModel):
    email: str
    otp: str

# -----------------------------
#  Send OTP
# -----------------------------
@router.post("/send-otp")
async def send_otp(data: EmailRequest):
    otp = str(random.randint(100000, 999999))

    otp_store[data.email] = {
        "otp": otp,
        "expires": datetime.now(timezone.utc) + timedelta(minutes=5),
        "name": data.name if data.name else None
    }

    try:
        await send_email(
            data.email,
            "Your OTP Code",
            f"Hello,\n\nYour OTP is: {otp}\nExpires in 5 minutes."
        )
    except Exception as e:
        raise HTTPException(500, f"Email failed: {str(e)}")

    return {"message": "OTP sent successfully"}

# -----------------------------
#  Verify OTP
# -----------------------------
@router.post("/verify-otp")
async def verify_otp(data: VerifyOTP, request: Request):
    record = otp_store.get(data.email)

    if not record:
        raise HTTPException(400, "No OTP found")

    if record["otp"] != data.otp:
        raise HTTPException(400, "Invalid OTP")

    if datetime.now(timezone.utc) > record["expires"]:
        raise HTTPException(400, "OTP expired")

    # 🌐 Get IP
    user_ip = request.headers.get("x-forwarded-for")
    if user_ip:
        user_ip = user_ip.split(",")[0]
    else:
        user_ip = request.client.host

    #  Check DB
    existing_user = await users_collection.find_one({"email": data.email})

    if not existing_user:
        #  New user
        final_name = record["name"] if record["name"] else None

        await users_collection.insert_one({
            "username": final_name,
            "email": data.email,
            "created_at": datetime.now(timezone.utc),
            "ip": user_ip,
            "history": []
        })
    else:
        # 👤 Existing user
        final_name = existing_user.get("username")

    #  JWT
    token = create_token(data.email)

    # cleanup
    otp_store.pop(data.email, None)

    #  Display name logic
    display_name = final_name if final_name else data.email

    return {
        "message": "Login successful",
        "name": display_name,
        "email": data.email,
        "token": token,
        "is_new_user": not existing_user
    }