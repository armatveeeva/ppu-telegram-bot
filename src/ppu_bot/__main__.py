import asyncio
import logging

from aiogram import Bot, Dispatcher
from pydantic import ValidationError

from .config import get_settings

logger = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    try:
        settings = get_settings()
    except ValidationError as exc:
        fields = ", ".join(str(err["loc"][0]) for err in exc.errors())
        raise SystemExit(
            f"Отсутствуют или некорректны переменные окружения: {fields}. Проверьте файл .env"
        ) from exc

    bot = Bot(token=settings.bot_token.get_secret_value())
    dp = Dispatcher()

    from .handlers import proposal

    dp.include_router(proposal.router)

    logger.info("Бот запущен, ожидаю сообщения")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
