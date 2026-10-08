"""
Fetch a URL and extract readable text from it, so it can go through the
same chunk -> embed -> store pipeline as /ingest and /ingest-file.

Reuses extract_text_from_upload() for binary types like PDF (so PDF
handling logic lives in exactly one place), and falls back to stripping
HTML tags for regular web pages.
"""
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from file_extraction import extract_text_from_upload

REQUEST_TIMEOUT = 15  # seconds
MAX_CONTENT_BYTES = 10 * 1024 * 1024  # 10 MB safety cap


def extract_text_from_url(url: str) -> str:
    """
    Fetch `url` and return extracted plain text.

    Raises requests.RequestException on network/HTTP errors, and
    ValueError if the response is too large to ingest.
    """
    response = requests.get(
        url,
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": "local-rag-ingest/1.0"},
    )
    response.raise_for_status()

    content = response.content
    if len(content) > MAX_CONTENT_BYTES:
        raise ValueError(f"Content too large ({len(content)} bytes) to ingest from {url}")

    content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()

    # PDF served from a URL: reuse the same extraction path as file uploads
    if content_type == "application/pdf" or url.lower().endswith(".pdf"):
        filename = urlparse(url).path.rsplit("/", 1)[-1] or "downloaded.pdf"
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"
        return extract_text_from_upload(filename, content)

    # Regular web page: strip tags, scripts, styles, nav/boilerplate
    if "html" in content_type or not content_type:
        soup = BeautifulSoup(content, "html.parser")
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines()]
        return "\n".join(line for line in lines if line)

    # Fallback: treat as plain text
    return content.decode("utf-8", errors="ignore")