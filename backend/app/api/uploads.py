from pathlib import Path
import re
import unicodedata
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile, status


router = APIRouter(prefix="/uploads", tags=["Documentos"])

PROJECT_ROOT = Path(__file__).resolve().parents[3]
UPLOAD_ROOT = PROJECT_ROOT / "storage"
DOCUMENTS_DIR = UPLOAD_ROOT / "documents"
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 20 * 1024 * 1024
ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".txt", ".csv", ".png", ".jpg", ".jpeg", ".webp",
}


def sanitize_filename(filename: str) -> str:
    original = Path(filename or "documento").name
    normalized = unicodedata.normalize("NFKD", original).encode("ascii", "ignore").decode()
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", normalized).strip(".-")
    return safe[:140] or "documento"


def validate_extension(filename: str) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(415, f"Tipo de arquivo nao permitido. Extensoes aceitas: {allowed}")
    return extension


@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...)):
    safe_original = sanitize_filename(file.filename or "documento")
    extension = validate_extension(safe_original)
    stored_name = f"{uuid4().hex}-{safe_original}"
    target = DOCUMENTS_DIR / stored_name
    size = 0
    try:
        with target.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    raise HTTPException(413, "O arquivo excede o limite de 20 MB")
                output.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    display_name = Path(safe_original).stem.replace("-", " ").replace("_", " ").strip()
    return {
        "name": display_name or "Documento",
        "filename": safe_original,
        "url": f"/uploads/documents/{stored_name}",
        "size": size,
        "extension": extension,
    }
