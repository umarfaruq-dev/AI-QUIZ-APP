from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import quiz_route, user_route, auth_route, stats_route

app = FastAPI(
    title="AI Quiz App",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 🌍 allow all origins
    allow_credentials=False,  # ⚠️ must be False when using "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_route.router, prefix="/api/users", tags=["Users"])
app.include_router(quiz_route.router, prefix="/api/quiz", tags=["Quiz"])
app.include_router(auth_route.router, prefix="/api/auth", tags=["Auth"])
app.include_router(stats_route.router, prefix="/api")

@app.get("/")
async def root():
    return {"status": "Backend running "}