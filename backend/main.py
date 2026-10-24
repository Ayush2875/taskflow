import os
import time
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import ValidationError
from jose import JWTError

import models
import schemas
import algorithms
import parser as quick_add_parser
import real_llm
import auth
from database import engine, SessionLocal, Base

USE_REAL_LLM = os.environ.get("USE_REAL_LLM", "false").lower() == "true"
PRIORITY_RANK = {"low": 1, "medium": 2, "high": 3}

Base.metadata.create_all(bind=engine)

app = FastAPI(title="TaskFlow API")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Auth: HTTPBearer reads the "Authorization: Bearer <token>" header and makes
# the "Authorize" button in /docs accept a pasted token. auto_error=False
# means a request with no token reaches our own code (credentials=None), so
# we return our own 401 message instead of FastAPI's generic one.
# ---------------------------------------------------------------------------
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    unauthorized = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    try:
        payload = auth.decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id is None:
            raise unauthorized
    except JWTError:
        raise unauthorized

    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if user is None:
        raise unauthorized
    return user


@app.middleware("http")
async def log_requests(request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    print(f"{request.method} {request.url.path} completed in {duration_ms:.2f}ms")
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://taskflow-98k.pages.dev"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# ===========================================================================
# AUTH
# ===========================================================================

@app.post("/auth/login", response_model=schemas.Token)
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == credentials.email).first()
    if not user or not auth.verify_password(credentials.password, user.password_hash):
        # Deliberately the SAME error for "no such user" and "wrong password" —
        # revealing which one it was would let an attacker enumerate which
        # emails are registered.
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    access_token = auth.create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


# ===========================================================================
# USERS (registration lives here — POST /users doubles as "sign up")
# ===========================================================================

@app.post("/users", response_model=schemas.UserOut, status_code=201)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=422, detail="Email already registered")

    db_user = models.User(
        name=user.name,
        email=user.email,
        password_hash=auth.hash_password(user.password),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.get("/users", response_model=List[schemas.UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()


# ===========================================================================
# PROJECTS
# ===========================================================================

@app.post("/projects", response_model=schemas.ProjectOut, status_code=201)
def create_project(
    project: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_project = models.Project(name=project.name, owner_id=project.owner_id)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


@app.get("/projects", response_model=List[schemas.ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.query(models.Project).all()


@app.get("/projects/{project_id}/stats")
def project_stats(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    total = (
        db.query(func.count(models.Task.id))
        .filter(models.Task.project_id == project_id)
        .scalar()
    )

    by_priority_rows = (
        db.query(models.Task.priority, func.count(models.Task.id))
        .filter(models.Task.project_id == project_id)
        .group_by(models.Task.priority)
        .all()
    )
    by_priority = {priority: count for priority, count in by_priority_rows}

    return {"project_id": project_id, "total_tasks": total, "by_priority": by_priority}


# ===========================================================================
# TASKS — reads are public, writes require a valid token
# ===========================================================================

@app.post("/tasks", response_model=schemas.TaskOut, status_code=201)
def create_task(
    task: schemas.TaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    project = db.query(models.Project).filter(models.Project.id == task.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db_task = models.Task(
        title=task.title, priority=task.priority, due_date=task.due_date, project_id=task.project_id
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


@app.get("/tasks", response_model=List[schemas.TaskOut])
def list_tasks(sort: Optional[str] = None, db: Session = Depends(get_db)):
    db_tasks = db.query(models.Task).all()
    task_dicts = [
        {"id": t.id, "title": t.title, "priority": t.priority, "due_date": t.due_date, "project_id": t.project_id}
        for t in db_tasks
    ]

    if sort == "priority":
        for d in task_dicts:
            d["_sort_key"] = PRIORITY_RANK.get(d["priority"], 0)
        algorithms.insertion_sort(task_dicts, "_sort_key")
        for d in task_dicts:
            del d["_sort_key"]
    elif sort == "due_date":
        for d in task_dicts:
            d["_sort_key"] = d["due_date"] or ""
        algorithms.insertion_sort(task_dicts, "_sort_key")
        for d in task_dicts:
            del d["_sort_key"]
    elif sort is not None:
        raise HTTPException(status_code=422, detail="sort must be 'priority' or 'due_date'")

    return task_dicts


@app.get("/tasks/search", response_model=schemas.TaskOut)
def search_tasks(title: str, algo: str = "binary", db: Session = Depends(get_db)):
    if algo not in ("binary", "linear"):
        raise HTTPException(status_code=422, detail="algo must be 'binary' or 'linear'")

    db_tasks = db.query(models.Task).all()
    index = [{"id": t.id, "title": t.title} for t in db_tasks]

    if algo == "binary":
        algorithms.insertion_sort(index, "title")
        found_idx = algorithms.binary_search(index, title, "title")
    else:
        found_idx = algorithms.linear_search(index, title, "title")

    if found_idx == -1:
        raise HTTPException(status_code=404, detail="No task with that exact title")

    matched_id = index[found_idx]["id"]
    task = db.query(models.Task).filter(models.Task.id == matched_id).first()
    return task


@app.get("/tasks/{task_id}", response_model=schemas.TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.put("/tasks/{task_id}", response_model=schemas.TaskOut)
def update_task(
    task_id: int,
    task_update: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = task_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task


@app.delete("/tasks/{task_id}", status_code=200)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"detail": "Task deleted", "id": task_id}


# ===========================================================================
# Section 3: AI Quick-Add — also protected, since it creates a task
# ===========================================================================

def build_prompt_messages(description: str):
    system_message = {
        "role": "system",
        "content": (
            "You are a task-parsing assistant for TaskFlow. Given a free-text "
            "task description, extract a structured task with: title, priority "
            "(low/medium/high), and due_date_hint (a raw date phrase, or null)."
        ),
    }
    return [system_message, {"role": "user", "content": description}]


@app.post("/tasks/quick-add", response_model=schemas.TaskOut, status_code=201)
def quick_add_task(
    payload: schemas.QuickAddRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    project = db.query(models.Project).filter(models.Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(
            status_code=422, detail=f"project_id {payload.project_id} does not reference an existing project"
        )

    _messages = build_prompt_messages(payload.description)

    if USE_REAL_LLM:
        try:
            parsed = real_llm.call_real_llm(payload.description)
        except Exception as e:
            print(f"Real LLM call failed ({e}), falling back to mock parser")
            parsed = quick_add_parser.mock_parse(payload.description)
    else:
        parsed = quick_add_parser.mock_parse(payload.description)

    try:
        validated = schemas.TaskCreate(
            title=parsed["title"], priority=parsed["priority"],
            due_date=parsed["due_date_hint"], project_id=payload.project_id,
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    db_task = models.Task(
        title=validated.title, priority=validated.priority,
        due_date=validated.due_date, project_id=validated.project_id,
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task
