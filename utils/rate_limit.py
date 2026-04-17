from datetime import datetime, timedelta, timezone
from fastapi import HTTPException

async def check_limits(user, user_ip, users_collection, ip_logs_collection):
   
    print(f"Rate limiter : {user} and {user_ip}")
    now = datetime.now(timezone.utc)
    last_24h = now - timedelta(hours=24)

    # -----------------------------
    # 🚫 GLOBAL IP LIMIT (20/day)
    # -----------------------------
    ip_count = await ip_logs_collection.count_documents({
        "ip": user_ip,
        "time": {"$gte": last_24h}
    })

    if ip_count >= 15: 
        raise HTTPException(429, "Too many requests from this IP (15/day)")

    # -----------------------------
    # 👤 LOGGED USER LIMIT (3/day)
    # -----------------------------
    print(user ,users_collection)
    if user:
        attempts = [
            q for q in user.get("history", [])
            if isinstance(q.get("time"), datetime)
            and (now - (q["time"].replace(tzinfo=timezone.utc)
                if q["time"].tzinfo is None else q["time"])) <= timedelta(hours=24)
        ]

        if len(attempts) >= 5:
            raise HTTPException(429, "Limit: 5 quizzes per 24 hours")

    # -----------------------------
    # 👻 GUEST LIMIT (2/day)
    # -----------------------------
    else:
        guest_count = await ip_logs_collection.count_documents({
            "ip": user_ip,
            "time": {"$gte": last_24h}
        })

        if guest_count >= 2:
            raise HTTPException(429, "Guest limit: 2 quizzes per day, login for geeting 5 quizzes per day")

    return now