import asyncio
from pathlib import Path

from pyzipper import WZ_AES, AESZipFile

TEMP_DIR = Path("temp_output")
EXCEL_FILE = Path("Реестр ППУ.xlsx")
DOCS_DIR = Path("ППУ_документы")
PHOTOS_DIR = Path("ППУ_фото")

TEMP_DIR.mkdir(exist_ok=True)


async def create_archive(
    proposal_id: int,
    doc_path: Path,
    photo_before_name: str | None,
    photo_after_name: str | None,
    password: str,
) -> Path:
    archive_path = TEMP_DIR / f"ППУ_{proposal_id}_архив.zip"

    def _zip():
        with AESZipFile(archive_path, "w", encryption=WZ_AES) as zf:
            zf.setpassword(password.encode("utf-8"))
            zf.write(doc_path, doc_path.name)
            zf.write(EXCEL_FILE, EXCEL_FILE.name)
            if photo_before_name and (PHOTOS_DIR / photo_before_name).exists():
                zf.write(PHOTOS_DIR / photo_before_name, f"{PHOTOS_DIR.name}/{photo_before_name}")
            if photo_after_name and (PHOTOS_DIR / photo_after_name).exists():
                zf.write(PHOTOS_DIR / photo_after_name, f"{PHOTOS_DIR.name}/{photo_after_name}")

    await asyncio.to_thread(_zip)
    return archive_path


async def cleanup_files(
    doc_path: Path, archive_path: Path, photo_before_name: str | None, photo_after_name: str | None
):
    def _remove():
        for f in [doc_path, archive_path]:
            if f and f.exists():
                f.unlink(missing_ok=True)
        for pname in [photo_before_name, photo_after_name]:
            if pname:
                p = PHOTOS_DIR / pname
                if p.exists():
                    p.unlink(missing_ok=True)

    await asyncio.to_thread(_remove)
