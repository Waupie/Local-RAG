import io
from typing import Optional

import pdfplumber


def extract_text_from_upload(filename: str, content: bytes) -> str:
    if filename.lower().endswith(".pdf"):
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        return "\n".join(pages).strip()
    return content.decode("utf-8", errors="ignore").strip()
