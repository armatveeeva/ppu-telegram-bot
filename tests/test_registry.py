"""Тесты репозитория registry — запись в Excel с моком файловой системы."""

import asyncio
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from openpyxl import load_workbook

from ppu_bot.repositories.registry import EXPECTED_HEADERS, add_proposal

SAMPLE_ROW: dict[str, Any] = {
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


@pytest.fixture()
def excel_path(tmp_path: Path) -> Path:
    return tmp_path / "Реестр ППУ.xlsx"


@pytest.fixture(autouse=True)
def patch_excel_path(
    excel_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[None, None, None]:
    import ppu_bot.repositories.registry as reg_module

    monkeypatch.setattr(reg_module, "EXCEL_FILE", excel_path)
    monkeypatch.setattr(reg_module, "excel_lock", asyncio.Lock())
    yield


class TestAddProposal:
    async def test_creates_excel_if_not_exists(self, excel_path: Path) -> None:
        assert not excel_path.exists()  # noqa: ASYNC240
        await add_proposal(SAMPLE_ROW)
        assert excel_path.exists()  # noqa: ASYNC240

    async def test_excel_has_correct_headers(self, excel_path: Path) -> None:
        await add_proposal(SAMPLE_ROW)
        wb = load_workbook(excel_path)
        ws = wb["proposals"]
        headers = [ws.cell(row=1, column=i + 1).value for i in range(len(EXPECTED_HEADERS))]
        assert headers == EXPECTED_HEADERS

    async def test_first_proposal_gets_id_1(self, excel_path: Path) -> None:
        assert await add_proposal(SAMPLE_ROW) == 1

    async def test_second_proposal_gets_id_2(self, excel_path: Path) -> None:
        await add_proposal(SAMPLE_ROW)
        assert await add_proposal(SAMPLE_ROW) == 2

    async def test_ids_increment_sequentially(self, excel_path: Path) -> None:
        ids = [await add_proposal(SAMPLE_ROW) for _ in range(5)]
        assert ids == [1, 2, 3, 4, 5]

    async def test_data_written_to_row(self, excel_path: Path) -> None:
        await add_proposal(SAMPLE_ROW)
        wb = load_workbook(excel_path)
        ws = wb["proposals"]
        assert ws.cell(row=2, column=2).value == SAMPLE_ROW["submission_date"]
        assert ws.cell(row=2, column=3).value == SAMPLE_ROW["department"]
        assert ws.cell(row=2, column=4).value == SAMPLE_ROW["fio"]

    async def test_photo_names_written(self, excel_path: Path) -> None:
        await add_proposal(SAMPLE_ROW)
        wb = load_workbook(excel_path)
        ws = wb["proposals"]
        assert ws.cell(row=2, column=10).value == "before.jpg"
        assert ws.cell(row=2, column=11).value == "after.jpg"

    async def test_missing_photos_default_to_dash(self, excel_path: Path) -> None:
        row: dict[str, Any] = {
            k: v
            for k, v in SAMPLE_ROW.items()
            if k not in ("photo_before_name", "photo_after_name")
        }
        await add_proposal(row)
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
        tasks = [add_proposal(SAMPLE_ROW) for _ in range(5)]
        ids = await asyncio.gather(*tasks)
        assert len(set(ids)) == 5
