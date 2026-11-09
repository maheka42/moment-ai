"""Safe text extraction from supported MOMENT AI input files."""
from pathlib import Path

import fitz
from fastapi import HTTPException

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".mp3", ".wav", ".m4a", ".ogg", ".webm"}


def get_file_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def extract_pdf(data: bytes) -> str:
    try:
        with fitz.open(stream=data, filetype="pdf") as pdf:
            if pdf.is_encrypted:
                raise HTTPException(status_code=400, detail="Password-protected PDFs are not supported.")
            pages = []
            for page_number, page in enumerate(pdf, start=1):
                page_text = page.get_text("text").strip()
                if page_text:
                    pages.append(f"[Source: page {page_number}]\n{page_text}")
            if not pages:
                raise HTTPException(
                    status_code=422,
                    detail="No selectable text found. Scanned PDF OCR is not supported yet.",
                )
            return "\n\n".join(pages)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not read this PDF.") from exc


def extract_text_file(data: bytes) -> str:
    try:
        text = data.decode("utf-8-sig").strip()
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="TXT file must be UTF-8 encoded.") from exc
    if not text:
        raise HTTPException(status_code=422, detail="The uploaded text file is empty.")
    return text
