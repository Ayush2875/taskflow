"""
models.py
---------
These are SQLAlchemy ORM models — Python classes that map directly to
database tables. Each class attribute becomes a column.

Relationships:
  User (1) ---- (many) Project (1) ---- (many) Task

back_populates is what makes `a_project.tasks` and `a_task.project` both
work — it tells SQLAlchemy the two relationship() calls are two sides of
the same link, so it keeps them in sync automatically.
"""

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)  # UNIQUE constraint

    # One user -> many projects
    projects = relationship("Project", back_populates="owner")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Many projects -> one user
    owner = relationship("User", back_populates="projects")
    # One project -> many tasks
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    # Closed set enforced at the Pydantic layer (schemas.py), stored as plain
    # string here — SQLite has no native ENUM type.
    priority = Column(String, nullable=False, default="medium")
    # Intentionally plain text, not Date — see brief: both a manually typed
    # date ("2026-08-10") and an AI-parsed phrase ("next friday") must fit.
    due_date = Column(String, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    # Many tasks -> one project
    project = relationship("Project", back_populates="tasks")
