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

DOCS_DIR.mkdir(exist_ok=True)
PHOTOS_DIR.mkdir(exist_ok=True)


async def generate_document(data: ProposalData, bot: Bot) -> tuple[Path, str | None, str | None]:
    context = data.model_dump()

    async def process_photo(file_id: str | None, prefix: str) -> tuple[str, bytes] | None:
        if not file_id:
            return None
        file = await bot.get_file(file_id)
        photo_bytes = await bot.download_file(file.file_path)
        filename = f"temp_{prefix}.jpg"
        return filename, photo_bytes

    before_task = process_photo(data.photo_before_file_id, "до") if data.photo_before_file_id else None
    after_task = process_photo(data.photo_after_file_id, "после") if data.photo_after_file_id else None

    results = await asyncio.gather(
        before_task if before_task else asyncio.sleep(0, result=None),
        after_task if after_task else asyncio.sleep(0, result=None)
    )

    doc = DocxTemplate(TEMPLATES_DIR / ("Бланк_ППУ.docx" if data.has_photos else "Бланк_ППУ_2.docx"))

    photo_before_name, photo_after_name = None, None

    if results[0]:
        fname, pbytes = results[0]
        photo_before_name = fname
        context["photo_before"] = InlineImage(doc, io.BytesIO(pbytes), width=Mm(80))
    else:
        context["photo_before"] = ""

    if results[1]:
        _fname, pbytes = results[1]  # Префикс _ показывает, что переменная не используется
        photo_after_name = fname
        context["photo_after"] = InlineImage(doc, io.BytesIO(pbytes), width=Mm(80))
    else:
        context["photo_after"] = ""

    def _render():
        doc.render(context)
        doc_path = DOCS_DIR / f"ППУ_{context.get('id', 'temp')}.docx"
        doc.save(doc_path)
        return doc_path

    doc_path = await asyncio.to_thread(_render)

    if results[0]:
        await asyncio.to_thread(lambda: (PHOTOS_DIR / results[0][0]).write_bytes(results[0][1]))
    if results[1]:
        await asyncio.to_thread(lambda: (PHOTOS_DIR / results[1][0]).write_bytes(results[1][1]))

    return doc_path, photo_before_name, photo_after_name
