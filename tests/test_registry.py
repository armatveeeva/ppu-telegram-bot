"""Тесты репозитория registry — запись в Excel с моком файловой системы."""

import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest
from openpyxl import load_workbook

from ppu_bot.repositories.registry import EXPECTED_HEADERS, add_proposal

# ---------------------------------------------------------------------------
# Вспомогательные данные
# ---------------------------------------------------------------------------

SAMPLE_ROW: dict = {
    "submission_date": "01.01.2025",
    "department": "Отдел тестирования",
    "fio": "Тестов Тест Тестович",
    "position": "Тестировщик",
    "process": "Тестирование",
    "problem": "Нет автотестов",
    "solution": "Написать автотесты",
    "result": "Покрытие 80%",
    "reward": "100%",
    "photo_before_name": "before.jpg",
    "photo_after_name": "after.jpg",
}


# ---------------------------------------------------------------------------
# Фикстуры
# ---------------------------------------------------------------------------


@pytest.fixture()
def excel_path(tmp_path: Path) -> Path:
    """Временный путь для Excel-файла, изолированный от рабочей директории."""
    return tmp_path / "Реестр ППУ.xlsx"


@pytest.fixture(autouse=True)
def patch_excel_path(excel_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Подменяем EXCEL_FILE в модуле на временный путь."""
    import ppu_bot.repositories.registry as reg_module

    monkeypatch.setattr(reg_module, "EXCEL_FILE", excel_path)
    monkeypatch.setattr(reg_module, "excel_lock", asyncio.Lock())


# ---------------------------------------------------------------------------
# Тесты
# ---------------------------------------------------------------------------


class TestAddProposal:
    async def test_creates_excel_if_not_exists(self, excel_path: Path) -> None:
        assert not excel_path.exists()
        await add_proposal(SAMPLE_ROW)
        assert excel_path.exists()

    async def test_excel_has_correct_headers(self, excel_path: Path) -> None:
        await add_proposal(SAMPLE_ROW)
        wb = load_workbook(excel_path)
        ws = wb["proposals"]
        headers = [ws.cell(row=1, column=i + 1).value for i in range(len(EXPECTED_HEADERS))]
        assert headers == EXPECTED_HEADERS

    async def test_first_proposal_gets_id_1(self, excel_path: Path) -> None:
        proposal_id = await add_proposal(SAMPLE_ROW)
        assert proposal_id == 1

    async def test_second_proposal_gets_id_2(self, excel_path: Path) -> None:
        await add_proposal(SAMPLE_ROW)
        proposal_id = await add_proposal(SAMPLE_ROW)
        assert proposal_id == 2

    async def test_ids_increment_sequentially(self, excel_path: Path) -> None:
        ids = [await add_proposal(SAMPLE_ROW) for _ in range(5)]
        assert ids == [1, 2, 3, 4, 5]

    async def test_data_written_to_row(self, excel_path: Path) -> None:
        await add_proposal(SAMPLE_ROW)
        wb = load_workbook(excel_path)
        ws = wb["proposals"]
        row_values = [ws.cell(row=2, column=i + 1).value for i in range(len(EXPECTED_HEADERS))]
        assert row_values[1] == SAMPLE_ROW["submission_date"]
        assert row_values[2] == SAMPLE_ROW["department"]
        assert row_values[3] == SAMPLE_ROW["fio"]

    async def test_photo_names_written(self, excel_path: Path) -> None:
        await add_proposal(SAMPLE_ROW)
        wb = load_workbook(excel_path)
        ws = wb["proposals"]
        assert ws.cell(row=2, column=10).value == "before.jpg"
        assert ws.cell(row=2, column=11).value == "after.jpg"

    async def test_missing_photos_default_to_dash(self, excel_path: Path) -> None:
        row_no_photos = {k: v for k, v in SAMPLE_ROW.items()
                         if k not in ("photo_before_name", "photo_after_name")}
        await add_proposal(row_no_photos)
        wb = load_workbook(excel_path)
        ws = wb["proposals"]
        assert ws.cell(row=2, column=10).value == "-"
        assert ws.cell(row=2, column=11).value == "-"

    async def test_status_column_empty_on_creation(self, excel_path: Path) -> None:
        await add_proposal(SAMPLE_ROW)
        wb = load_workbook(excel_path)
        ws = wb["proposals"]
        assert ws.cell(row=2, column=len(EXPECTED_HEADERS)).value == ""

    async def test_concurrent_writes_no_duplicate_ids(self, excel_path: Path) -> None:
        """Параллельные запросы не должны давать одинаковые ID."""
        tasks = [add_proposal(SAMPLE_ROW) for _ in range(5)]
        ids = await asyncio.gather(*tasks)
        assert len(set(ids)) == 5