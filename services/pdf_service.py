import fitz
from docx import Document


def extract_text(file_path: str):
    try:
        # ✅ PDF
        if file_path.endswith(".pdf"):
            doc = fitz.open(file_path)
            pages = []

            for page in doc:
                text = page.get_text().strip().replace("\n", " ")
                if text:
                    pages.append(text)

            doc.close()
            return pages

        # ✅ DOCX
        elif file_path.endswith(".docx"):
            doc = Document(file_path)
            text = []

            for para in doc.paragraphs:
                if para.text.strip():
                    text.append(para.text.strip())

            return text

        else:
            return {"error": "Unsupported file type"}

    except Exception as e:
        return {"error": str(e)}