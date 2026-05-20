from pydantic import BaseModel, Field
from typing import Optional
import json


class PaperBase(BaseModel):
    title: str = ""
    authors: str = ""
    year: Optional[int] = None
    venue: str = ""
    tags: list[str] = Field(default_factory=list)
    read: bool = False
    note: str = ""
    bibtex: str = ""


class PaperCreate(BaseModel):
    file_path: str


class PaperUpdate(BaseModel):
    title: Optional[str] = None
    authors: Optional[str] = None
    year: Optional[int] = None
    venue: Optional[str] = None
    tags: Optional[list[str]] = None
    read: Optional[bool] = None
    note: Optional[str] = None
    bibtex: Optional[str] = None


class SpeedReadData(BaseModel):
    status: str = "pending"
    one_sentence: str = ""
    quick_takeaways: list[str] = Field(default_factory=list)
    problem_and_motivation: str = ""
    method_overview: str = ""
    method_steps: list[str] = Field(default_factory=list)
    core_figures: list[dict] = Field(default_factory=list)
    experiment_read: str = ""
    contributions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    deep_read_suggestions: list[str] = Field(default_factory=list)
    model_used: str = ""
    tokens_used: int = 0
    error_message: str = ""


class PaperResponse(PaperBase):
    id: str
    file_path: str
    date_added: str = ""
    page_count: int = 0
    file_size: int = 0
    speed_read: Optional[SpeedReadData] = None

    @classmethod
    def from_row(cls, row: dict, speed_read_row: dict | None = None):
        tags = json.loads(row.get("tags", "[]")) if isinstance(row.get("tags"), str) else row.get("tags", [])
        sr = None
        # LEFT JOIN 可能返回全是 NULL 的 speed_read 行，用 paper_id 判空
        if speed_read_row and speed_read_row.get("paper_id") is not None:
            sr = SpeedReadData(
                status=speed_read_row.get("status", "pending"),
                one_sentence=speed_read_row.get("one_sentence", ""),
                quick_takeaways=_parse_json_list(speed_read_row.get("quick_takeaways")),
                problem_and_motivation=speed_read_row.get("problem_and_motivation", ""),
                method_overview=speed_read_row.get("method_overview", ""),
                method_steps=_parse_json_list(speed_read_row.get("method_steps")),
                core_figures=_parse_json_list(speed_read_row.get("core_figures")),
                experiment_read=speed_read_row.get("experiment_read", ""),
                contributions=_parse_json_list(speed_read_row.get("contributions")),
                limitations=_parse_json_list(speed_read_row.get("limitations")),
                deep_read_suggestions=_parse_json_list(speed_read_row.get("deep_read_suggestions")),
                model_used=speed_read_row.get("model_used", ""),
                tokens_used=speed_read_row.get("tokens_used", 0),
                error_message=speed_read_row.get("error_message", ""),
            )
        return cls(
            id=row["id"],
            file_path=row["file_path"],
            title=row.get("title", ""),
            authors=row.get("authors", ""),
            year=row.get("year"),
            venue=row.get("venue", ""),
            tags=tags,
            read=bool(row.get("read", 0)),
            note=row.get("note", ""),
            bibtex=row.get("bibtex", ""),
            date_added=row.get("date_added", ""),
            page_count=row.get("page_count", 0),
            file_size=row.get("file_size", 0),
            speed_read=sr,
        )


def _parse_json_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
    return []
