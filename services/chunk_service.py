import re

def chunk_text(text, chunk_size=500, overlap=50, max_chars=6000):
    sentences = re.split(r'(?<=[.!?]) +', text)

    chunks = []
    current_chunk = ""
    total_length = 0

    for sentence in sentences:
        if total_length + len(sentence) > max_chars:
            break  # 🛑 stop at ~2 pages

        if len(current_chunk) + len(sentence) > chunk_size:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())

            words = current_chunk.split()
            current_chunk = " ".join(words[-overlap:])

        current_chunk += " " + sentence
        total_length += len(sentence)

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks