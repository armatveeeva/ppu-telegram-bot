"""Тесты модели ProposalData — валидация полей."""

from typing import Any

import pytest
from pydantic import ValidationError

from ppu_bot.models import MAX_TEXT, ProposalData

VALID_DATA: dict[str, Any] = {
    "department": "Отдел логистики",
    "process": "Приёмка товара",
    "fio": "Иванов Иван Иванович",
    "position": "Менеджер",
    "reward": "100%",
    "problem": "Проблема занимает много времени",
    "solution": "Автоматизировать проверку через QR",
    "result": "Снижение времени приёмки на 30%",
}


def make_proposal(**overrides: Any) -> ProposalData:
    return ProposalData(**{**VALID_DATA, **overrides})


class TestProposalDataValid:
    def test_creates_with_valid_data(self) -> None:
        p = make_proposal()
        assert p.department == "Отдел логистики"
        assert p.fio == "Иванов Иван Иванович"

    def test_submission_date_auto_filled(self) -> None:
        p = make_proposal()
        parts = p.submission_date.split(".")
        assert len(parts) == 3
        assert len(parts[2]) == 4

    def test_photos_optional_default_none(self) -> None:
        p = make_proposal()
        assert p.photo_before_file_id is None
        assert p.photo_after_file_id is None

    def test_has_photos_false_without_photos(self) -> None:
        assert make_proposal().has_photos is False

    def test_has_photos_true_with_before(self) -> None:
        assert make_proposal(photo_before_file_id="file123").has_photos is True

    def test_has_photos_true_with_after(self) -> None:
        assert make_proposal(photo_after_file_id="file456").has_photos is True

    def test_has_photos_true_with_both(self) -> None:
        assert make_proposal(photo_before_file_id="b", photo_after_file_id="a").has_photos is True


class TestStripWhitespace:
    def test_department_stripped(self) -> None:
        assert make_proposal(department="  Отдел  ").department == "Отдел"

    def test_fio_stripped(self) -> None:
        assert make_proposal(fio="  Иванов Иван Иванович  ").fio == "Иванов Иван Иванович"

    def test_problem_stripped(self) -> None:
        p = make_proposal(problem="  " + "А" * 10 + "  ")
        assert not p.problem.startswith(" ")
        assert not p.problem.endswith(" ")


class TestFieldLengths:
    def test_department_min_length_ok(self) -> None:
        make_proposal(department="АБ")

    def test_department_too_short_raises(self) -> None:
        with pytest.raises(ValidationError):
            make_proposal(department="А")

    def test_fio_min_length_ok(self) -> None:
        make_proposal(fio="А Б В Г")

    def test_fio_too_short_raises(self) -> None:
        with pytest.raises(ValidationError):
            make_proposal(fio="Ив")

    def test_problem_exactly_min_length(self) -> None:
        make_proposal(problem="А" * 10)

    def test_problem_below_min_length_raises(self) -> None:
        with pytest.raises(ValidationError):
            make_proposal(problem="Коротко")

    def test_problem_exactly_max_length(self) -> None:
        make_proposal(problem="А" * MAX_TEXT)

    def test_problem_over_max_length_raises(self) -> None:
        with pytest.raises(ValidationError):
            make_proposal(problem="А" * (MAX_TEXT + 1))

    def test_solution_over_max_length_raises(self) -> None:
        with pytest.raises(ValidationError):
            make_proposal(solution="Б" * (MAX_TEXT + 1))

    def test_result_over_max_length_raises(self) -> None:
        with pytest.raises(ValidationError):
            make_proposal(result="В" * (MAX_TEXT + 1))


class TestRequiredFields:
    @pytest.mark.parametrize(
        "field",
        ["department", "process", "fio", "position", "reward", "problem", "solution", "result"],
    )
    def test_missing_required_field_raises(self, field: str) -> None:
        data: dict[str, Any] = {k: v for k, v in VALID_DATA.items() if k != field}
        with pytest.raises(ValidationError):
            ProposalData(**data)
