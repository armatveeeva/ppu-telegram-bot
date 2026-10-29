import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message
from pydantic import ValidationError

from ..config import get_settings
from ..models import MAX_TEXT, ProposalData
from ..repositories import registry
from ..services import archive, document
from ..states import ProposalForm

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == "Заполнить ППУ")
@router.message(F.command == "fill")
async def start_form(message: Message, state: FSMContext):
    await state.set_state(ProposalForm.department)
    await message.answer("Укажите Ваше подразделение:")


@router.message(ProposalForm.department)
async def process_department(message: Message, state: FSMContext):
    await state.update_data(department=message.text)
    await state.set_state(ProposalForm.process)
    await message.answer("Укажите улучшаемый процесс (операцию):")


@router.message(ProposalForm.process)
async def process_process(message: Message, state: FSMContext):
    await state.update_data(process=message.text)
    await state.set_state(ProposalForm.fio)
    await message.answer("Укажите Ваше ФИО:")


@router.message(ProposalForm.fio)
async def process_fio(message: Message, state: FSMContext):
    await state.update_data(fio=message.text)
    await state.set_state(ProposalForm.position)
    await message.answer("Укажите Вашу должность:")


@router.message(ProposalForm.position)
async def process_position(message: Message, state: FSMContext):
    await state.update_data(position=message.text)
    await state.set_state(ProposalForm.reward)
    await message.answer("Укажите распределение вознаграждения, %:")


@router.message(ProposalForm.reward)
async def process_reward(message: Message, state: FSMContext):
    await state.update_data(reward=message.text)
    await state.set_state(ProposalForm.problem)
    await message.answer(f"Опишите проблему (до {MAX_TEXT} символов):")


@router.message(ProposalForm.problem)
async def process_problem(message: Message, state: FSMContext):
    if len(message.text) > MAX_TEXT:
        await message.answer(
            f"Слишком длинный текст ({len(message.text)} / {MAX_TEXT}). Попробуйте снова."
        )
        return
    await state.update_data(problem=message.text)
    await state.set_state(ProposalForm.solution)
    await message.answer(f"Опишите решение (до {MAX_TEXT} символов):")


@router.message(ProposalForm.solution)
async def process_solution(message: Message, state: FSMContext):
    if len(message.text) > MAX_TEXT:
        await message.answer(
            f"Слишком длинный текст ({len(message.text)} / {MAX_TEXT}). Попробуйте снова."
        )
        return
    await state.update_data(solution=message.text)
    await state.set_state(ProposalForm.result)
    await message.answer(f"Опишите результат (до {MAX_TEXT} символов):")


@router.message(ProposalForm.result)
async def process_result(message: Message, state: FSMContext):
    if len(message.text) > MAX_TEXT:
        await message.answer(
            f"Слишком длинный текст ({len(message.text)} / {MAX_TEXT}). Попробуйте снова."
        )
        return
    await state.update_data(result=message.text)
    await state.set_state(ProposalForm.photo_before)
    await message.answer("Прикрепите фото ДО (или напишите «нет»):")


@router.message(ProposalForm.photo_before, F.text)
async def process_photo_before_text(message: Message, state: FSMContext):
    if message.text.strip().lower() == "нет":
        await state.update_data(photo_before_file_id=None)
        await state.set_state(ProposalForm.photo_after)
        await message.answer("Прикрепите фото ПОСЛЕ (или напишите «нет»):")
    else:
        await message.answer("Пожалуйста, прикрепите фото или напишите «нет».")


@router.message(ProposalForm.photo_before, F.photo)
async def process_photo_before_photo(message: Message, state: FSMContext):
    await state.update_data(photo_before_file_id=message.photo[-1].file_id)
    await state.set_state(ProposalForm.photo_after)
    await message.answer("Прикрепите фото ПОСЛЕ (или напишите «нет»):")


@router.message(ProposalForm.photo_after, F.text)
async def process_photo_after_text(message: Message, state: FSMContext, bot: Bot):
    if message.text.strip().lower() == "нет":
        await state.update_data(photo_after_file_id=None)
        await finalize_proposal(message, state, bot)
    else:
        await message.answer("Пожалуйста, прикрепите фото или напишите «нет».")


@router.message(ProposalForm.photo_after, F.photo)
async def process_photo_after_photo(message: Message, state: FSMContext, bot: Bot):
    await state.update_data(photo_after_file_id=message.photo[-1].file_id)
    await finalize_proposal(message, state, bot)


async def finalize_proposal(message: Message, state: FSMContext, bot: Bot):
    await message.answer("Обрабатываю вашу заявку...")
    data = await state.get_data()

    try:
        proposal = ProposalData(**data)
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        await message.answer(
            "Ошибка валидации данных. Пожалуйста, начните заполнение заново (/fill)."
        )
        await state.clear()
        return

    settings = get_settings()
    doc_path = photo_b_name = photo_a_name = archive_path = None

    try:
        doc_path, photo_b_name, photo_a_name = await document.generate_document(proposal, bot)

        proposal_id = await registry.add_proposal(
            {
                "submission_date": proposal.submission_date,
                "department": proposal.department,
                "fio": proposal.fio,
                "position": proposal.position,
                "process": proposal.process,
                "problem": proposal.problem,
                "solution": proposal.solution,
                "result": proposal.result,
                "reward": proposal.reward,
                "photo_before_name": photo_b_name or "-",
                "photo_after_name": photo_a_name or "-",
            }
        )

        archive_path = await archive.create_archive(
            proposal_id,
            doc_path,
            photo_b_name,
            photo_a_name,
            settings.archive_password.get_secret_value(),
        )

        file_to_send = FSInputFile(archive_path)
        await bot.send_document(
            chat_id=settings.admin_chat_id,
            document=file_to_send,
            caption=f"Новая заявка ППУ №{proposal_id}",
        )

        await message.answer(
            f"Заявка ППУ №{proposal_id} успешно сохранена, зашифрована и отправлена администратору."
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке ППУ: {e}", exc_info=True)
        await message.answer(
            "Произошла ошибка при сохранении заявки. Пожалуйста, сообщите администратору."
        )

    finally:
        await state.clear()
        if doc_path or archive_path:
            await archive.cleanup_files(doc_path, archive_path, photo_b_name, photo_a_name)
