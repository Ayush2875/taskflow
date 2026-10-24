from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, field_validator

# --- Users -----------------------------------------------------------------

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    # Deliberately no password_hash here — this schema is what gets sent
    # back to the client, and the hash should never leave the server.

    class Config:
        from_attributes = True


# --- Auth --------------------------------------------------------------------

class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


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

class TaskCreate(BaseModel):
    title: str
    priority: Literal["low", "medium", "high"] = "medium"
    due_date: Optional[str] = None
    project_id: int

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title must not be blank")
        return v


class TaskUpdate(BaseModel):
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
