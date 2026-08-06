from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, field_validator

# --- Users -----------------------------------------------------------------

class UserCreate(BaseModel):
    name: str
    email: EmailStr


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr

    class Config:
        from_attributes = True  # lets Pydantic read straight from ORM objects


# --- Projects ----------------------------------------------------------------

class ProjectCreate(BaseModel):
    name: str
    owner_id: int


class ProjectOut(BaseModel):
    id: int
    name: str
    owner_id: int

    class Config:
        from_attributes = True


# --- Tasks -------------------------------------------------------------------

# Literal["low", "medium", "high"] IS the Field constraint the brief asks
# for: FastAPI will reject (422) any priority value outside this closed set
# automatically, before your endpoint code even runs.

class TaskCreate(BaseModel):
    title: str
    priority: Literal["low", "medium", "high"] = "medium"
    due_date: Optional[str] = None
    project_id: int

    # Custom validator: reject a blank title after trimming whitespace.
    # This is the "at least one custom validator" requirement from the brief.
    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title must not be blank")
        return v


class TaskUpdate(BaseModel):
    # All optional so PATCH-style partial updates are possible.
    title: Optional[str] = None
    priority: Optional[Literal["low", "medium", "high"]] = None
    due_date: Optional[str] = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("title must not be blank")
        return v


class TaskOut(BaseModel):
    id: int
    title: str
    priority: str
    due_date: Optional[str]
    project_id: int

    class Config:
        from_attributes = True


# --- AI Quick-Add (Section 3) ------------------------------------------------

class QuickAddRequest(BaseModel):
    description: str
    project_id: int