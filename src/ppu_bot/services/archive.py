"""
Сервис для создания зашифрованных ZIP-архивов и очистки временных файлов.
Использует pyzipper для шифрования AES-256.
"""

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
    """
    Создает зашифрованный ZIP-архив с документом, реестром и фотографиями.

    :param proposal_id: ID предложения для именования архива
    :param doc_path: Путь к сгенерированному .docx файлу
    :param photo_before_name: Имя файла фото "До" (или None)
    :param photo_after_name: Имя файла фото "После" (или None)
    :param password: Пароль для шифрования архива
    :return: Путь к созданному архиву
    """
    archive_path = TEMP_DIR / f"ППУ_{proposal_id}_архив.zip"

    def _zip_files() -> Path:
        with AESZipFile(archive_path, 'w', encryption=WZ_AES) as zf:
            zf.setpassword(password.encode('utf-8'))

            zf.write(doc_path, doc_path.name)

            if EXCEL_FILE.exists():
                zf.write(EXCEL_FILE, EXCEL_FILE.name)

            if photo_before_name:
                p_before = PHOTOS_DIR / photo_before_name
                if p_before.exists():
                    zf.write(p_before, f"{PHOTOS_DIR.name}/{photo_before_name}")

            if photo_after_name:
                p_after = PHOTOS_DIR / photo_after_name
                if p_after.exists():
                    zf.write(p_after, f"{PHOTOS_DIR.name}/{photo_after_name}")

        return archive_path

    return await asyncio.to_thread(_zip_files)


async def cleanup_files(
        doc_path: Path,
        archive_path: Path,
        photo_before_name: str | None,
        photo_after_name: str | None,
) -> None:
    """
    Безопасно удаляет временные файлы после успешной отправки архива.

    :param doc_path: Путь к .docx файлу
    :param archive_path: Путь к созданному .zip архиву
    :param photo_before_name: Имя файла фото "До"
    :param photo_after_name: Имя файла фото "После"
    """

    def _remove_files() -> None:
        for file_path in [doc_path, archive_path]:
            if file_path and file_path.exists():
                file_path.unlink(missing_ok=True)

        for photo_name in [photo_before_name, photo_after_name]:
            if photo_name:
                photo_path = PHOTOS_DIR / photo_name
                if photo_path.exists():
                    photo_path.unlink(missing_ok=True)

    await asyncio.to_thread(_remove_files)
