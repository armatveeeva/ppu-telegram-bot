from datetime import datetime
from pydantic import BaseModel, Field, field_validator

MAX_TEXT = 3500


class ProposalData(BaseModel):
    """Данные формы ППУ, собранные в диалоге."""
    submission_date: str = Field(default_factory=lambda: datetime.now().strftime("%d.%m.%Y"))
    department: str = Field(min_length=2, max_length=100)
    process: str = Field(min_length=3, max_length=200)
    fio: str = Field(min_length=5, max_length=100)
    position: str = Field(min_length=2, max_length=100)
    reward: str = Field(min_length=1, max_length=100)
    problem: str = Field(min_length=10, max_length=MAX_TEXT)
    solution: str = Field(min_length=10, max_length=MAX_TEXT)
    result: str = Field(min_length=10, max_length=MAX_TEXT)

    photo_before_file_id: str | None = None
    photo_after_file_id: str | None = None

    @field_validator(
        "department", "process", "fio", "position", "reward",
        "problem", "solution", "result",
    )
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()

    @property
    def has_photos(self) -> bool:
        return bool(self.photo_before_file_id or self.photo_after_file_id)
