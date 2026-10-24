# TaskFlow

A full-stack task and project management platform for Blinkit's dark-store engineering pods.

- **Section 1 — Core app:** FastAPI + SQLAlchemy + SQLite backend with JWT authentication, and a vanilla HTML/CSS/JS dashboard.
- **Section 2 — Algorithms engine:** hand-written insertion sort, binary search and linear search that power two of the backend's own endpoints.
- **Section 3 — AI quick-add:** turns one plain-English sentence into a structured task, using a deterministic, keyless rule-based parser (with an optional free local-LLM path).

Everything runs in one backend service on one database (`users`, `projects`, `tasks`). **No paid service or API key is needed anywhere.**

---

## Contents

1. [Environment setup](#1-environment-setup)
2. [Running the app locally](#2-running-the-app-locally)
3. [Authentication](#3-authentication)
4. [Database schema](#4-database-schema)
5. [Endpoint list](#5-endpoint-list)
6. [Section 2 — Algorithms: complexity and benchmark](#6-section-2--algorithms-complexity-and-benchmark)
7. [Section 3 — AI quick-add](#7-section-3--ai-quick-add)
8. [Configuration (environment variables)](#8-configuration-environment-variables)
9. [Testing](#9-testing)
10. [Repository structure](#10-repository-structure)
11. [Git workflow](#11-git-workflow)

---

## 1. Environment setup

From the repository root:

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

`requirements.txt` installs FastAPI, Uvicorn, SQLAlchemy, Pydantic (with email validation), `bcrypt` (password hashing) and `python-jose` (JWT). All are free and open source.

> **Upgrading from an earlier version?** The `users` table gained a `password_hash` column and the project has no migration tool, so delete the old database file once (`backend/taskflow.db`). A fresh one is created automatically on startup.

---

## 2. Running the app locally

TaskFlow uses a **two-process run**: the backend serves the API on port 8000, and the frontend is served as static files on port 5500.

**Terminal 1 — backend:**
```bash
cd backend
uvicorn main:app --reload
```
The API is now at `http://127.0.0.1:8000`, with interactive docs at `http://127.0.0.1:8000/docs`. `taskflow.db` is created automatically on first run.

**Terminal 2 — frontend:**
```bash
cd frontend
python -m http.server 5500
```
Open `http://127.0.0.1:5500` in your browser. (VS Code's Live Server extension also serves on port 5500.)

**First use:**
1. On the dashboard, open the **Register** tab and create an account. You are logged in automatically.
2. On a fresh database, the first login creates a project named "Dark Store Ops" for you. The dashboard shows the first project that exists.
3. Add, edit and delete tickets. Reading the list never requires an account.

> The backend's CORS configuration explicitly allows `http://127.0.0.1:5500` and `http://localhost:5500`, with the methods `GET, POST, PUT, DELETE, OPTIONS` and the headers `Content-Type` and `Authorization`. If you serve the frontend from a different port, update `allow_origins` in `backend/main.py`. The frontend calls the backend at `http://127.0.0.1:8000` (`API_BASE` in `frontend/script.js`).

---

## 3. Authentication

TaskFlow uses **JWT bearer tokens**.

| Item | Detail |
|---|---|
| Passwords | Hashed with `bcrypt` (salted). Plain passwords are never stored or returned. Minimum 8 characters. |
| Login | `POST /auth/login` with email and password returns a signed token. |
| Token | HS256-signed JWT, expires after 60 minutes. The `sub` claim holds the user id. |
| Sending it | `Authorization: Bearer <token>` header. |
| Secret key | Read from the `JWT_SECRET_KEY` environment variable. If unset, an insecure development default is used and a warning is printed at startup. |
| Failed login | Wrong email and wrong password return the same message, so the endpoint cannot be used to discover which emails are registered. |

**What is protected:** every endpoint that changes data — `POST /projects`, `POST /tasks`, `PUT /tasks/{id}`, `DELETE /tasks/{id}` and `POST /tasks/quick-add`. They return `401` without a valid token. Every `GET` endpoint, `POST /users` (registration) and `POST /auth/login` are public.

**Using it in Swagger (`/docs`):** call `POST /auth/login`, copy the `access_token` value, click **Authorize**, paste the token (without the word "Bearer") and confirm.

**Using it with curl:**
```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "asha@blinkit.com", "password": "securepass123"}'

curl -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <paste token here>" \
  -d '{"title": "Restock shelf A", "priority": "high", "project_id": 1}'
```

**Known limitations:**
- This is *authentication* only. There are no ownership checks, so any logged-in user can edit or delete any task.
- There are no refresh tokens or token revocation, and no login rate limiting.
- The dashboard keeps the token in `localStorage`, which is convenient but readable by any script on the page. This is why the dashboard builds all task elements with `textContent` and never inserts user text with `innerHTML`.

---

## 4. Database schema

Three tables, defined as SQLAlchemy ORM models in `backend/models.py`.

```
users
  id             INTEGER  PRIMARY KEY
  name           TEXT     NOT NULL
  email          TEXT     NOT NULL  UNIQUE
  password_hash  TEXT     NOT NULL

projects
  id             INTEGER  PRIMARY KEY
  name           TEXT     NOT NULL
  owner_id       INTEGER  NOT NULL  FOREIGN KEY -> users.id

tasks
  id             INTEGER  PRIMARY KEY
  title          TEXT     NOT NULL
  priority       TEXT     NOT NULL  (low | medium | high, enforced by Pydantic)
  due_date       TEXT     NULL      (raw text: "2026-08-10" and "next friday" are both valid)
  project_id     INTEGER  NOT NULL  FOREIGN KEY -> projects.id
```

Relationships use `relationship()` with `back_populates` on both sides: `user.projects` / `project.owner`, and `project.tasks` / `task.project`.

---

## 5. Endpoint list

13 endpoints. "Auth" shows whether a Bearer token is required.

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/auth/login` | no | Log in, receive a JWT |
| POST | `/users` | no | Register a user |
| GET | `/users` | no | List users |
| POST | `/projects` | **yes** | Create a project |
| GET | `/projects` | no | List projects |
| GET | `/projects/{project_id}/stats` | no | Task counts for a project |
| POST | `/tasks` | **yes** | Create a task |
| GET | `/tasks` | no | List tasks (`?sort=priority` or `?sort=due_date`) |
| GET | `/tasks/search` | no | Exact-title search (`?title=...&algo=binary\|linear`) |
| GET | `/tasks/{task_id}` | no | Get one task |
| PUT | `/tasks/{task_id}` | **yes** | Update a task |
| DELETE | `/tasks/{task_id}` | **yes** | Delete a task |
| POST | `/tasks/quick-add` | **yes** | Create a task from free text |

### Login

**`POST /auth/login`**
```json
// Request
{"email": "asha@blinkit.com", "password": "securepass123"}

// Response (200)
{"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", "token_type": "bearer"}
```
Returns `401` with `{"detail": "Incorrect email or password"}` on bad credentials.

### Create

**`POST /users`** — register (public)
```json
// Request
{"name": "Asha", "email": "asha@blinkit.com", "password": "securepass123"}

// Response (201) — the password hash is never returned
{"id": 1, "name": "Asha", "email": "asha@blinkit.com"}
```
Returns `422` for a password under 8 characters, an invalid email, or an email that is already registered.

**`POST /projects`** — requires `Authorization: Bearer <token>`
```json
// Request
{"name": "Dark Store Ops", "owner_id": 1}

// Response (201)
{"id": 1, "name": "Dark Store Ops", "owner_id": 1}
```

**`POST /tasks`** — requires `Authorization: Bearer <token>`
```json
// Request
{"title": "Restock shelf A", "priority": "high", "project_id": 1}

// Response (201)
{"id": 1, "title": "Restock shelf A", "priority": "high", "due_date": null, "project_id": 1}
```
Returns `401` without a valid token, `422` for a blank title or a priority outside `low`/`medium`/`high`, and `404` if `project_id` does not exist.

### List

**`GET /users`**, **`GET /projects`**, **`GET /tasks`** — all public
```json
// GET /tasks — Response (200)
[{"id": 1, "title": "Restock shelf A", "priority": "high", "due_date": null, "project_id": 1}]
```

### Get by id

**`GET /tasks/{task_id}`**
```json
// Response (200)
{"id": 1, "title": "Restock shelf A", "priority": "high", "due_date": null, "project_id": 1}
```
Returns `404` if the id does not exist.

### Update

**`PUT /tasks/{task_id}`** — requires `Authorization: Bearer <token>`; partial updates are supported
```json
// Request
{"priority": "low"}

// Response (200)
{"id": 1, "title": "Restock shelf A", "priority": "low", "due_date": null, "project_id": 1}
```
Returns `401` without a valid token, `404` if the id does not exist, and `422` for invalid values.

### Delete

**`DELETE /tasks/{task_id}`** — requires `Authorization: Bearer <token>`
```json
// Response (200)
{"detail": "Task deleted", "id": 1}
```
Returns `401` without a valid token and `404` if the id does not exist.

### Statistics

**`GET /projects/{project_id}/stats`** — counts are computed in SQL with `COUNT` and `GROUP BY`, not in Python
```json
// Response (200)
{"project_id": 1, "total_tasks": 3, "by_priority": {"high": 1, "medium": 1, "low": 1}}
```
Returns `404` if the project does not exist.

### Sorted list

**`GET /tasks?sort=priority`** — ordered by the project's own `insertion_sort`, not by the database or Python's built-in sort. `sort=due_date` is also supported.
```json
// Response (200) — low, then medium, then high
[
  {"id": 1, "title": "Zebra crate check", "priority": "low", "due_date": null, "project_id": 1},
  {"id": 3, "title": "Middle audit", "priority": "medium", "due_date": null, "project_id": 1},
  {"id": 2, "title": "Alpha restock", "priority": "high", "due_date": null, "project_id": 1}
]
```
Returns `422` for any other `sort` value.

### Search

**`GET /tasks/search?title=<exact title>&algo=binary|linear`** — `binary` (the default) sorts an in-memory index with `insertion_sort` and then runs `binary_search`; `linear` runs `linear_search` over the unsorted index.
```json
// GET /tasks/search?title=Alpha restock&algo=binary — Response (200)
{"id": 2, "title": "Alpha restock", "priority": "high", "due_date": null, "project_id": 1}
```
Returns `404` if no task has that exact title and `422` for an unknown `algo`.

### Quick-add

**`POST /tasks/quick-add`** — requires `Authorization: Bearer <token>`
```json
// Request
{"description": "This is urgent, mark it ASAP please", "project_id": 1}

// Response (201)
{"id": 1, "title": "This is , mark it please", "priority": "high", "due_date": null, "project_id": 1}
```
Returns `401` without a valid token. Returns `422`, and writes no row, if the body is malformed (for example, a missing `description`) or `project_id` does not reference an existing project.

---

## 6. Section 2 — Algorithms: complexity and benchmark

The functions live in `backend/algorithms.py`. `binary_search` and `linear_search` return the index of a match, or **`-1`** if the target is absent.

### Time complexity

| Function | Best case | Worst case |
|---|---|---|
| `insertion_sort` | O(n) — already sorted | O(n²) — reverse-sorted or random order |
| `binary_search` | O(1) — target at the midpoint | O(log n) |
| `linear_search` | O(1) — target at the first index | O(n) — target absent or last |

### Benchmark results

Raw comparison counts from `backend/benchmark.py`, produced by the counting wrappers (`insertion_sort_count`, `binary_search_count`, `linear_search_count`) on synthetic task data with the same `title`/`priority`/`due_date` fields the endpoints use. The generator uses a fixed seed (42), so the numbers are reproducible. The full table is saved in `backend/benchmark_results.md`.

| Size | insertion_sort | binary_search (present) | binary_search (absent) | linear_search (present) | linear_search (absent) |
|---|---|---|---|---|---|
| 10 | 29 | 4 | 3 | 4 | 10 |
| 500 | 63,132 | 9 | 9 | 326 | 500 |
| 3,000 | 2,246,602 | 12 | 11 | 1,195 | 3,000 |

### Is sorting first worth it?

Sorting is the expensive step. At 3,000 tasks, `insertion_sort` needs about 2.2 million comparisons, and its cost grows roughly with n²: going from 500 to 3,000 tasks multiplied the count by about 36. `binary_search` needs only 12 comparisons at 3,000 tasks, matching log₂(3000) ≈ 11.5, and `linear_search` needs up to 3,000. TaskFlow teams list and sort their tasks repeatedly through the day but add or rename tasks less often, so one sort can serve many lookups, and each later lookup costs about 12 comparisons instead of up to n. The trade-off would flip if edits were far more frequent than reads, because each edit could force a re-sort. At production scale, the sort should move into the database (`ORDER BY`) or use an O(n log n) algorithm; insertion sort is used here because the brief requires a hand-written one.

### Running the checks and benchmark

```bash
cd backend
python check_algorithms.py   # prints one PASS/FAIL line for each of the 12 cases
python benchmark.py          # prints the table above and writes benchmark_results.md
```

---

## 7. Section 3 — AI quick-add

`POST /tasks/quick-add` builds a role-based prompt (a system message describing the parsing task and a user message carrying the free text), parses it, validates the result against the same `TaskCreate` model the CRUD endpoints use, and only then writes a row to the `tasks` table. The default parser is the deterministic mock in `backend/parser.py`: **zero network calls, zero API keys.**

### The parsing rules

1. Lower-case a working copy for matching only; the title is built from the original-cased text.
2. **Priority** — first matching group wins: `urgent` or `asap` → `high`; otherwise `whenever` or `low priority` → `low`; otherwise `medium`.
3. **Due-date hint** — first match wins, in this order: `today`, `tomorrow`, `next week`, `next monday` … `next sunday`, then bare `monday` … `sunday`. The hint is stored as the matched lower-case phrase, or `null`.
4. **Title** — remove every occurrence of every priority keyword found (from both groups) and of the matched date phrase, collapse leftover whitespace, and strip the ends. If nothing is left, the title is `"Untitled task"`.

### Prompting technique rationale

The system message and mock parser are modeled on **zero-shot, rule-based extraction**, not few-shot or chain-of-thought. The system message states the task directly: extract `title`, `priority` and `due_date_hint` from free text. It contains no example input/output pairs (few-shot) and does not ask the model to reason step by step first (chain-of-thought).

This fits because the extraction follows a small, closed set of surface-level keyword rules rather than nuanced judgment. A direct instruction states the *what*, and the rules fix the *how*, so examples add little.

**Token usage:** few-shot would resend several example conversations with every request, multiplying cost for marginal gain, and chain-of-thought would add reasoning tokens to every call. Zero-shot keeps each request to one short instruction plus the user's sentence.

**Reliability:** chain-of-thought also adds variability, because a model reasoning aloud can phrase things differently from run to run, while this feature needs identical input to give identical output. A strict JSON-only zero-shot instruction keeps the output shape predictable, and every result is validated before it is saved. The required mock mirrors the prompt with hand-written rules, so it is fully deterministic and is what runs by default. The optional local-model path uses the same prompt and falls back to the mock on any failure.

### Five worked examples

Each output is exactly what `mock_parse` returns for that input.

| # | Input | Output |
|---|---|---|
| 1 | `"Please water the plants whenever you get a chance"` | `{"title": "Please water the plants you get a chance", "priority": "low", "due_date_hint": null}` |
| 2 | `"Submit the invoice today, low priority though"` | `{"title": "Submit the invoice , though", "priority": "low", "due_date_hint": "today"}` |
| 3 | `"Call the vendor next Monday urgent"` | `{"title": "Call the vendor", "priority": "high", "due_date_hint": "next monday"}` |
| 4 | `"Clean the warehouse floor"` | `{"title": "Clean the warehouse floor", "priority": "medium", "due_date_hint": null}` |
| 5 | `"asap fix the broken freezer door next week"` | `{"title": "fix the broken freezer door", "priority": "high", "due_date_hint": "next week"}` |

Check the brief's own four worked examples with:
```bash
cd backend
python parser.py
```

### Optional: a free local LLM

The mock is the required, graded path. If you want to try a real model, `backend/real_llm.py` can call a **local, free** model through [Ollama](https://ollama.com) (open source, runs on your machine, no account or key):

```bash
ollama pull llama3.2
set USE_REAL_LLM=true          # Windows (use `export` on macOS/Linux)
uvicorn main:app --reload
```

The flag defaults to **off**. If Ollama is not running, or the model returns unusable output, the endpoint logs the problem and falls back to the mock automatically, so quick-add never fails because of the optional path.

---

## 8. Configuration (environment variables)

All optional. The app runs with none of them set.

| Variable | Default | Purpose |
|---|---|---|
| `JWT_SECRET_KEY` | insecure dev value (warning printed) | Signs and verifies JWTs. Set a long random value for anything beyond local use. |
| `USE_REAL_LLM` | `false` | Turns on the optional local-LLM path for quick-add. |
| `OLLAMA_HOST` | `http://localhost:11434` | Where to reach Ollama. |
| `OLLAMA_MODEL` | `llama3.2` | Which local model to use. |

---

## 9. Testing

```bash
cd backend
python check_algorithms.py   # 12 PASS/FAIL checks for the algorithms and counting wrappers
python parser.py             # the brief's 4 worked examples, checked against the mock parser
python benchmark.py          # comparison-count benchmark
```

The API was also exercised manually through Swagger (`/docs`) and `curl`: success and failure status codes for every endpoint, the 401 cases for protected endpoints, 422 validation cases, and checks that rejected requests wrote no row. The setup was verified from a fresh clone. There is not yet an automated pytest suite for the API.

---

## 10. Repository structure

```
taskflow/
├── backend/
│   ├── main.py               # FastAPI app: routes, auth dependency, middleware, CORS
│   ├── auth.py               # password hashing (bcrypt) and JWT create/verify
│   ├── database.py           # SQLAlchemy engine and session
│   ├── models.py             # ORM models: User, Project, Task
│   ├── schemas.py            # Pydantic request/response models
│   ├── algorithms.py         # insertion_sort, binary_search, linear_search + counting wrappers
│   ├── parser.py             # deterministic mock parser for quick-add
│   ├── real_llm.py           # optional local-LLM (Ollama) path, off by default
│   ├── seed.py               # synthetic task data for the benchmark
│   ├── benchmark.py          # runs the counting wrappers at 10 / 500 / 3000 records
│   ├── check_algorithms.py   # PASS/FAIL checks script
│   ├── benchmark_results.md  # saved raw benchmark output
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── script.js
└── README.md
```

---

## 11. Git workflow

Work was done on feature branches, each committed to more than once and merged back into `main` with `--no-ff`, so the branch shape is visible in `git log --graph --all`:

- `feature/frontend-dashboard`
- `feature/algorithms-core`
- `feature/algorithms-api`
- `feature/ai-quickadd`
- `feature/jwt-auth`
