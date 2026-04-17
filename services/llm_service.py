from groq import AsyncGroq
import json
import os
from dotenv import load_dotenv
import itertools
from datetime import datetime, timezone

from database import quiz_collection  # ✅ added

load_dotenv()

# -----------------------------
# 🔐 Load API Keys
# -----------------------------
api_key_1 = os.getenv("GROQ_API_KEY_1")
api_key_2 = os.getenv("GROQ_API_KEY_2")

if not api_key_1 or not api_key_2:
    raise ValueError("Both GROQ_API_KEY_1 and GROQ_API_KEY_2 are required")

# -----------------------------
# 🤖 Create Clients
# -----------------------------
client1 = AsyncGroq(api_key=api_key_1)
client2 = AsyncGroq(api_key=api_key_2)

# 🔁 Round-robin toggle
clients = [client1, client2]
client_cycle = itertools.cycle(clients)


# -----------------------------
# 🧠 Generate Quiz
# -----------------------------
async def generate_quiz(context: str, num_questions: int = 5):
    print(context)

    prompt = f"""
Generate exactly {num_questions} MCQ questions based ONLY on the content below.

CONTENT:
{context}

Strict rules:
- Return ONLY valid JSON
- No markdown, no explanation
- JSON must be an array
- The questions and options are in same input language 
- Exactly {num_questions} questions
- Each must have:
  - "question" (string)
  - "options" (4 items)
  - "answer" (must match exactly one option)

Format:
[
  {{
    "question": "string",
    "options": ["option1", "option2", "option3", "option4"],
    "answer": "one of the options exactly"
  }}
]
"""

    try:
        # 🔁 Toggle client
        client = next(client_cycle)

        if client == client1:
            print("Using GROQ API KEY 1")
        else:
            print("Using GROQ API KEY 2")

        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )

        content = response.choices[0].message.content.strip()

        # -----------------------------
        # 🔥 CLEAN RESPONSE
        # -----------------------------
        if "```" in content:
            parts = content.split("```")
            content = parts[1] if len(parts) > 1 else parts[0]
            content = content.replace("json", "").strip()

        start = content.find("[")
        end = content.rfind("]") + 1
        content = content[start:end]

        data = json.loads(content)

        # -----------------------------
        # 🔍 VALIDATION
        # -----------------------------
        if not isinstance(data, list) or len(data) != num_questions:
            return {"error": "Invalid structure from LLM", "raw": data}

        questions, options, answers = [], [], []

        for q in data:
            if not all(k in q for k in ["question", "options", "answer"]):
                return {"error": "Missing keys in response", "raw": q}

            if len(q["options"]) != 4:
                return {"error": "Options count not 4", "raw": q}

            questions.append(q["question"])
            options.append(q["options"])

            if q["answer"] in q["options"]:
                answers.append(q["options"].index(q["answer"]))
            else:
                answers.append(0)

        result = {
            "questions": questions,
            "options": options,
            "answers": answers
        }

        # -----------------------------
        #  SAVE QUIZ (SIMPLE)
        # -----------------------------
        try:
            await quiz_collection.insert_one({
                "quiz": result,
                "created_at": datetime.now(timezone.utc)
            })
        except Exception as db_err:
            print("DB save failed:", str(db_err))

        return result

    except json.JSONDecodeError:
        return {
            "error": "Invalid JSON from LLM",
            "raw": content
        }

    except Exception as e:
        return {
            "error": str(e)
        }