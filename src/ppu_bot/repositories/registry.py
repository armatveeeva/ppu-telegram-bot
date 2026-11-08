import asyncio
from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook

EXCEL_FILE = Path("Реестр ППУ.xlsx")
excel_lock = asyncio.Lock()

EXPECTED_HEADERS = [
    "№ ППУ",
    "Дата подачи",
    "Подразделение",
    "ФИО",
    "Должность",
    "Краткое наименование улучшаемого процесса",
    "Описание проблемы",
    "Предлагаемое изменение",
    "Результат",
    'Фото "До"',
    'Фото "После"',
    "Распределение вознаграждения,%",
    "Статус",
]


def _ensure_excel_exists() -> None:
    if not EXCEL_FILE.exists():
        wb = Workbook()
        ws = wb.active
        assert ws is not None, "openpyxl вернул None вместо активного листа"
        ws.title = "proposals"
        ws.append(EXPECTED_HEADERS)
        wb.save(EXCEL_FILE)


async def add_proposal(data: dict[str, Any]) -> int:
    _ensure_excel_exists()
    async with excel_lock:

        def _write() -> int:
            wb = load_workbook(EXCEL_FILE)
            ws = wb["proposals"]

            next_id: int
            if ws.max_row == 1:
                next_id = 1
            else:
                last_id = ws.cell(row=ws.max_row, column=1).value
                next_id = (last_id if isinstance(last_id, int) else 0) + 1

            row: list[Any] = [
                next_id,
                data["submission_date"],
                data["department"],
                data["fio"],
                data["position"],
                data["process"],
                data["problem"],
                data["solution"],
                data["result"],
                data.get("photo_before_name", "-"),
                data.get("photo_after_name", "-"),
                data["reward"],
                "",
            ]
            ws.append(row)
            wb.save(EXCEL_FILE)
            return next_id

        return await asyncio.to_thread(_write)
