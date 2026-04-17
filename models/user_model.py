from pydantic import BaseModel
from typing import List, Dict

class User(BaseModel):
    username: str
    email: str
    history: List[Dict] = []