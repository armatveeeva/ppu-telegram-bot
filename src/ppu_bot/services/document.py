import asyncio
import io
from pathlib import Path

from aiogram import Bot
from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage

from ..models import ProposalData

TEMPLATES_DIR = Path("templates")
DOCS_DIR = Path("ППУ_документы")
PHOTOS_DIR = Path("ППУ_фото")


async def _maybe_download(bot: Bot, file_id: str | None, prefix: str) -> tuple[str, bytes] | None:
    """Скачать фото по file_id или вернуть None. Выделено отдельно для корректного вывода типов."""
    if file_id is None:
        return None
    file = await bot.get_file(file_id)
    assert file.file_path is not None, f"file_path is None для file_id={file_id}"
    bio = await bot.download_file(file.file_path)
    assert bio is not None, f"download вернул None для file_id={file_id}"
    return f"temp_{prefix}.jpg", bio.read()


async def generate_document(data: ProposalData, bot: Bot) -> tuple[Path, str | None, str | None]:
    context = data.model_dump()

    result_before, result_after = await asyncio.gather(
        _maybe_download(bot, data.photo_before_file_id, "до"),
        _maybe_download(bot, data.photo_after_file_id, "после"),
    )

    doc = DocxTemplate(
        TEMPLATES_DIR / ("Бланк_ППУ.docx" if data.has_photos else "Бланк_ППУ_2.docx")
    )

    photo_before_name: str | None = None
    photo_after_name: str | None = None

    if result_before is not None:
        before_fname, before_bytes = result_before
        photo_before_name = before_fname
        context["photo_before"] = InlineImage(doc, io.BytesIO(before_bytes), width=Mm(80))
    else:
        context["photo_before"] = ""

    if result_after is not None:
        after_fname, after_bytes = result_after
        photo_after_name = after_fname  # исправлен баг: было fname вместо after_fname
        context["photo_after"] = InlineImage(doc, io.BytesIO(after_bytes), width=Mm(80))
    else:
        context["photo_after"] = ""

    def _render() -> Path:
        doc.render(context)
        doc_path = DOCS_DIR / f"ППУ_{context.get('id', 'temp')}.docx"
        doc.save(doc_path)
        return doc_path

    doc_path = await asyncio.to_thread(_render)

    if result_before is not None:
        bname, bbytes = result_before
        await asyncio.to_thread(lambda: (PHOTOS_DIR / bname).write_bytes(bbytes))
    if result_after is not None:
        aname, abytes = result_after
        await asyncio.to_thread(lambda: (PHOTOS_DIR / aname).write_bytes(abytes))

    return doc_path, photo_before_name, photo_after_name
