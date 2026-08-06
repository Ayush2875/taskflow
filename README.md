# TaskFlow

A full-stack task and project management platform built for Blinkit's dark-store engineering pods — a relational backend + dashboard (Section 1), a hand-rolled algorithms engine powering two of the backend's own endpoints (Section 2), and an AI-assisted quick-add feature that writes into the same task database everything else uses (Section 3).

---

## 1. Environment Setup

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

This installs FastAPI, Uvicorn, SQLAlchemy, and Pydantic (with email validation support).

---

## 2. Running the App Locally

TaskFlow uses a **two-process run**: the backend serves the API on one port, and the frontend is served as static files on a second port.

**Terminal 1 — start the backend:**
```bash
cd backend
uvicorn main:app --reload
```
This starts the API at `http://127.0.0.1:8000`. A `taskflow.db` SQLite file is created automatically on first run — no manual DB setup needed. Visit `http://127.0.0.1:8000/docs` for interactive API docs.

**Terminal 2 — serve the frontend:**
```bash
cd frontend
python -m http.server 5500
```
Then open `http://127.0.0.1:5500` in your browser.

> The backend's CORS configuration explicitly allows `http://127.0.0.1:5500` and `http://localhost:5500`. If you serve the frontend from a different port, update `allow_origins` in `backend/main.py` to match.

> **Note:** the dashboard is scoped to a single project (`PROJECT_ID = 1` in `frontend/script.js`). Create at least one user and one project via `POST /users` / `POST /projects` (e.g. through `/docs`) before using the dashboard's add-task form.

---

## 3. Full Endpoint List

### Users

**`POST /users`** — create a user
```json
// Request
{"name": "Asha", "email": "asha@blinkit.com"}

// Response (201)
{"id": 1, "name": "Asha", "email": "asha@blinkit.com"}
```

**`GET /users`** — list all users
```json
// Response (200)
[{"id": 1, "name": "Asha", "email": "asha@blinkit.com"}]
```

### Projects

**`POST /projects`** — create a project
```json
// Request
{"name": "Dark Store Ops", "owner_id": 1}

// Response (201)
{"id": 1, "name": "Dark Store Ops", "owner_id": 1}
```

**`GET /projects`** — list all projects
```json
// Response (200)
[{"id": 1, "name": "Dark Store Ops", "owner_id": 1}]
```

### Statistics

**`GET /projects/{project_id}/stats`** — per-project task counts, computed via SQL `COUNT`/`GROUP BY`
```json
// Response (200)
{"project_id": 1, "total_tasks": 3, "by_priority": {"high": 1, "medium": 1, "low": 1}}
```
Returns `404` if the project doesn't exist.

### Tasks — CRUD

**`POST /tasks`** — create a task
```json
// Request
{"title": "Restock shelf A", "priority": "high", "project_id": 1}

// Response (201)
{"id": 1, "title": "Restock shelf A", "priority": "high", "due_date": null, "project_id": 1}
```
Returns `422` if `title` is blank (after trimming) or `priority` isn't one of `low`/`medium`/`high`. Returns `404` if `project_id` doesn't exist.

**`GET /tasks`** — list all tasks
```json
// Response (200)
[{"id": 1, "title": "Restock shelf A", "priority": "high", "due_date": null, "project_id": 1}]
```

**`GET /tasks/{task_id}`** — get one task
```json
// Response (200)
{"id": 1, "title": "Restock shelf A", "priority": "high", "due_date": null, "project_id": 1}
```
Returns `404` if the id doesn't exist.

**`PUT /tasks/{task_id}`** — update a task (partial updates supported)
```json
// Request
{"priority": "low"}

// Response (200)
{"id": 1, "title": "Restock shelf A", "priority": "low", "due_date": null, "project_id": 1}
```
Returns `404` if the id doesn't exist, `422` on invalid values.

**`DELETE /tasks/{task_id}`**
```json
// Response (200)
{"detail": "Task deleted", "id": 1}
```
Returns `404` if the id doesn't exist.

### Tasks — Sorted List & Search (Section 2, algorithms engine)

**`GET /tasks?sort=priority`** (or `sort=due_date`) — returns tasks ordered by our own `insertion_sort`, not the DB's `ORDER BY` or Python's built-in sort
```json
// Response (200) — low, medium, high order
[
  {"id": 1, "title": "Zebra crate check", "priority": "low", "due_date": null, "project_id": 1},
  {"id": 3, "title": "Middle audit", "priority": "medium", "due_date": null, "project_id": 1},
  {"id": 2, "title": "Alpha restock", "priority": "high", "due_date": null, "project_id": 1}
]
```
Returns `422` if `sort` is anything other than `priority` or `due_date`.

**`GET /tasks/search?title=<exact title>&algo=binary|linear`** — finds an exact-title match using our own `binary_search` (default) or `linear_search`
```json
// Response (200)
{"id": 2, "title": "Alpha restock", "priority": "high", "due_date": null, "project_id": 1}
```
Returns `404` if no task has that exact title.

### AI Quick-Add (Section 3)

**`POST /tasks/quick-add`** — accepts free text, parses it (deterministic mock parser, zero API keys/network calls), creates a real task row
```json
// Request
{"description": "This is urgent, mark it ASAP please", "project_id": 1}

// Response (201)
{"id": 1, "title": "This is , mark it please", "priority": "high", "due_date": null, "project_id": 1}
```
Returns `422` if `project_id` doesn't reference an existing project, or if the body is malformed (e.g. missing `description`).

---

## 4. Section 2 — Algorithms: Complexity & Benchmark Analysis

### Time complexity

| Function | Best case | Worst case |
|---|---|---|
| `insertion_sort` | O(n) — already sorted | O(n²) — reverse sorted / random |
| `binary_search` | O(1) — target at midpoint | O(log n) |
| `linear_search` | O(1) — target at first index | O(n) — target absent or at the end |

### Benchmark evidence

Raw comparison counts from `benchmark.py` (see `backend/benchmark_results.md` for the full table), run against synthetic task data shaped like the real `title`/`priority`/`due_date` fields:

| Size | insertion_sort | binary_search | linear_search (absent) |
|---|---|---|---|
| 10 | 29 | 4 | 10 |
| 500 | 63,132 | 9 | 500 |
| 3,000 | 2,246,602 | 12 | 3,000 |

### Is sorting first worth it?

Sorting via `insertion_sort` is expensive relative to searching — at 3,000 tasks it takes over 2.2 million comparisons, growing roughly quadratically with size, while `binary_search` only needs about 12 comparisons per lookup regardless of scale (log₂3000 ≈ 11.5). Given how TaskFlow is actually used — a team lists and sorts their tasks repeatedly through the day, but adds or renames tasks comparatively rarely — the sort cost is paid once per view, then every subsequent search against that sorted view is nearly free by comparison. If tasks were instead searched with `linear_search`, every lookup would cost up to O(n) comparisons regardless of how many searches follow, which is worse than paying the sort cost once and reusing it. The tradeoff would flip only if edits (adds/renames) happened far more often than reads, since each edit could require re-sorting — but that's not this app's usage pattern.

**Run the checks and benchmark yourself:**
```bash
cd backend
python check_algorithms.py   # 12 PASS/FAIL lines, no assert/pytest
python benchmark.py          # prints the table above, saves benchmark_results.md
```

---

## 5. Section 3 — AI Quick-Add: Prompting Rationale & Worked Examples

### Prompting technique rationale

The system message and mock parser are modeled on a **zero-shot, rule-based extraction** approach rather than few-shot or chain-of-thought. The system message states the extraction task directly — pull out `title`, `priority`, and `due_date_hint` from free text — without providing example input/output pairs (few-shot) or asking the model to reason step-by-step before answering (chain-of-thought).

This choice fits the task well: the fields being extracted follow a small, fixed set of surface-level keyword rules (a handful of priority and date-phrase keywords), not a task requiring nuanced judgment or multi-step reasoning. A zero-shot instruction is enough to specify the *what*; it doesn't need worked examples to specify the *how*, since the parsing logic is closed-form rather than open-ended.

This matters for token usage and reliability: few-shot prompting would mean shipping several example conversations in every request just to anchor the model's behavior, multiplying token cost on every call for marginal gain here. Chain-of-thought would add reasoning tokens and, more importantly, non-determinism — an LLM "thinking out loud" through keyword matching could phrase its extraction differently each run, which is exactly what this feature can't tolerate (the brief requires the mock to be deterministic, so any two correct implementations produce identical output for the same input). A tightly-scoped zero-shot instruction keeps the request cheap and keeps output shape predictable, which is also why the mock parser mirrors it faithfully with hand-coded rules rather than any probabilistic behavior.

### Five worked examples

| # | Input | Output |
|---|---|---|
| 1 | `"Please water the plants whenever you get a chance"` | `{"title": "Please water the plants you get a chance", "priority": "low", "due_date_hint": null}` |
| 2 | `"Submit the invoice today, low priority though"` | `{"title": "Submit the invoice , though", "priority": "low", "due_date_hint": "today"}` |
| 3 | `"Call the vendor next Monday urgent"` | `{"title": "Call the vendor", "priority": "high", "due_date_hint": "next monday"}` |
| 4 | `"Clean the warehouse floor"` | `{"title": "Clean the warehouse floor", "priority": "medium", "due_date_hint": null}` |
| 5 | `"asap fix the broken freezer door next week"` | `{"title": "fix the broken freezer door", "priority": "high", "due_date_hint": "next week"}` |

**Run the parser's own worked-example check:**
```bash
cd backend
python parser.py   # verifies the brief's 4 worked examples match exactly
```

---

## 6. Repository Structure

```
taskflow/
├── backend/
│   ├── main.py              # FastAPI app: all routes, middleware, CORS
│   ├── database.py          # SQLAlchemy engine/session setup
│   ├── models.py            # ORM models: User, Project, Task
│   ├── schemas.py           # Pydantic request/response models
│   ├── algorithms.py        # insertion_sort, binary_search, linear_search + counting wrappers
│   ├── parser.py            # Section 3 deterministic mock parser
│   ├── seed.py               # synthetic data generator for benchmarking
│   ├── benchmark.py          # runs counting wrappers at 3 data sizes
│   ├── check_algorithms.py   # PASS/FAIL checks script
│   ├── benchmark_results.md  # raw benchmark output
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── script.js
└── README.md
```

## 7. Git Workflow

This repository's history includes three feature branches, each created, committed to at least twice, and merged back into `main` with `--no-ff` (visible via `git log --graph --all`):
- `feature/frontend-dashboard`
- `feature/algorithms-core` + `feature/algorithms-api`
- `feature/ai-quickadd`
