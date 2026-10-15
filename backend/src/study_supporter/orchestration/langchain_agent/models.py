"""Model-editable inputs contain no account, document, session or storage fields."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Query = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SearchInput(ToolInput):
    query: Query
    top_k: int = Field(default=3, ge=1, le=10)


class ProgressInput(ToolInput):
    pass


class QuizInput(ToolInput):
    topic: Query
    num_questions: int = Field(default=1, ge=1, le=15)


class SaveNoteInput(ToolInput):
    note: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
    operation_id: Annotated[str, StringConstraints(min_length=1, max_length=100)] | None = None
