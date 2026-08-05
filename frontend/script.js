/**
 * script.js
 * ---------
 * Talks to the TaskFlow FastAPI backend over Fetch. Renders the task list
 * into the DOM using createElement/appendChild (never innerHTML for
 * user-provided values — textContent only, to avoid injecting raw HTML).
 *
 * NOTE: This dashboard is scoped to a single project for simplicity —
 * PROJECT_ID below. Make sure a project with that id exists in your
 * database before using the form (create it via POST /projects, e.g.
 * through /docs, the same way we tested the backend earlier).
 */

const API_BASE = "http://127.0.0.1:8000";
const PROJECT_ID = 1;
const CACHE_KEY = `taskflow_cache_project_${PROJECT_ID}`;

const form = document.getElementById("task-form");
const titleInput = document.getElementById("title");
const dueDateInput = document.getElementById("due_date");
const priorityInput = document.getElementById("priority");
const titleError = document.getElementById("title-error");
const taskList = document.getElementById("task-list");
const taskCount = document.getElementById("task-count");
const emptyState = document.getElementById("empty-state");
const connectionStatus = document.getElementById("connection-status");

// ---------------------------------------------------------------------------
// Task 14: localStorage cache helpers
// ---------------------------------------------------------------------------
function readCache() {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (err) {
    console.error("Failed to read cache:", err);
    return [];
  }
}

function writeCache(tasks) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(tasks));
  } catch (err) {
    console.error("Failed to write cache:", err);
  }
}

// ---------------------------------------------------------------------------
// Task 11: Render the task list into the DOM using createElement/appendChild.
// Rebuilds the whole list each time — simple and correct for this app's size.
// ---------------------------------------------------------------------------
function renderTasks(tasks) {
  taskList.innerHTML = ""; // clearing the container itself is fine; only
                            // *user-provided values* must avoid innerHTML

  if (!tasks.length) {
    emptyState.hidden = false;
  } else {
    emptyState.hidden = true;
  }

  taskCount.textContent = `${tasks.length} task${tasks.length === 1 ? "" : "s"}`;

  tasks.forEach((task) => {
    taskList.appendChild(buildTaskElement(task));
  });
}

function buildTaskElement(task) {
  const item = document.createElement("div");
  item.className = `task-item priority-${task.priority}`;
  item.dataset.taskId = task.id;

  const main = document.createElement("div");
  main.className = "task-main";

  const title = document.createElement("p");
  title.className = "task-title";
  title.textContent = task.title; // textContent — safe for user input

  const meta = document.createElement("div");
  meta.className = "task-meta";

  const priorityTag = document.createElement("span");
  priorityTag.className = `priority-tag priority-${task.priority}`;
  priorityTag.textContent = task.priority;
  meta.appendChild(priorityTag);

  if (task.due_date) {
    const due = document.createElement("span");
    due.textContent = `due: ${task.due_date}`;
    meta.appendChild(due);
  }

  const idTag = document.createElement("span");
  idTag.textContent = `#${task.id}`;
  meta.appendChild(idTag);

  main.appendChild(title);
  main.appendChild(meta);

  const actions = document.createElement("div");
  actions.className = "task-actions";

  const editBtn = document.createElement("button");
  editBtn.type = "button";
  editBtn.className = "btn-icon";
  editBtn.textContent = "Edit";
  editBtn.addEventListener("click", () => enterEditMode(item, task));

  const deleteBtn = document.createElement("button");
  deleteBtn.type = "button";
  deleteBtn.className = "btn-icon danger";
  deleteBtn.textContent = "Delete";
  deleteBtn.addEventListener("click", () => handleDelete(task.id));

  actions.appendChild(editBtn);
  actions.appendChild(deleteBtn);

  item.appendChild(main);
  item.appendChild(actions);

  return item;
}

// ---------------------------------------------------------------------------
// Inline edit mode — swaps the item's content for editable fields.
// ---------------------------------------------------------------------------
function enterEditMode(item, task) {
  item.innerHTML = "";
  item.classList.add("editing");

  const titleField = document.createElement("input");
  titleField.type = "text";
  titleField.value = task.title;

  const editRow = document.createElement("div");
  editRow.className = "edit-row";

  const dueField = document.createElement("input");
  dueField.type = "text";
  dueField.placeholder = "due date";
  dueField.value = task.due_date || "";

  const priorityField = document.createElement("select");
  ["low", "medium", "high"].forEach((p) => {
    const opt = document.createElement("option");
    opt.value = p;
    opt.textContent = p;
    if (p === task.priority) opt.selected = true;
    priorityField.appendChild(opt);
  });

  const saveBtn = document.createElement("button");
  saveBtn.type = "button";
  saveBtn.className = "btn-icon";
  saveBtn.textContent = "Save";
  saveBtn.addEventListener("click", () => {
    const newTitle = titleField.value.trim();
    if (!newTitle) {
      titleField.setAttribute("aria-invalid", "true");
      return;
    }
    handleUpdate(task.id, {
      title: newTitle,
      due_date: dueField.value.trim() || null,
      priority: priorityField.value,
    });
  });

  const cancelBtn = document.createElement("button");
  cancelBtn.type = "button";
  cancelBtn.className = "btn-icon";
  cancelBtn.textContent = "Cancel";
  cancelBtn.addEventListener("click", () => loadTasks());

  editRow.appendChild(dueField);
  editRow.appendChild(priorityField);
  editRow.appendChild(saveBtn);
  editRow.appendChild(cancelBtn);

  item.appendChild(titleField);
  item.appendChild(editRow);
}

// ---------------------------------------------------------------------------
// Task 15: Fetch calls to the real backend
// ---------------------------------------------------------------------------
async function loadTasks() {
  try {
    const res = await fetch(`${API_BASE}/tasks`);
    if (!res.ok) throw new Error(`GET /tasks failed: ${res.status}`);
    const allTasks = await res.json();
    const tasks = allTasks.filter((t) => t.project_id === PROJECT_ID);

    connectionStatus.textContent = "live";
    connectionStatus.className = "header-status online";

    renderTasks(tasks);
    writeCache(tasks);
  } catch (err) {
    console.error(err);
    connectionStatus.textContent = "offline — showing cached data";
    connectionStatus.className = "header-status offline";
    // Cached copy is already rendered from the synchronous call in init(),
    // so there's nothing further to do here on failure.
  }
}

async function handleAdd(taskData) {
  try {
    const res = await fetch(`${API_BASE}/tasks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(taskData),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail ? JSON.stringify(body.detail) : `POST failed: ${res.status}`);
    }
    await loadTasks();
  } catch (err) {
    console.error("Failed to add task:", err);
    alert("Could not add task — check that the backend is running.");
  }
}

async function handleUpdate(taskId, updates) {
  try {
    const res = await fetch(`${API_BASE}/tasks/${taskId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates),
    });
    if (!res.ok) throw new Error(`PUT failed: ${res.status}`);
    await loadTasks();
  } catch (err) {
    console.error("Failed to update task:", err);
    alert("Could not update task — check that the backend is running.");
  }
}

async function handleDelete(taskId) {
  try {
    const res = await fetch(`${API_BASE}/tasks/${taskId}`, { method: "DELETE" });
    if (!res.ok) throw new Error(`DELETE failed: ${res.status}`);
    await loadTasks();
  } catch (err) {
    console.error("Failed to delete task:", err);
    alert("Could not delete task — check that the backend is running.");
  }
}

// ---------------------------------------------------------------------------
// Task 12/13: Form submit — preventDefault, client-side validation, addEventListener
// ---------------------------------------------------------------------------
form.addEventListener("submit", (event) => {
  event.preventDefault();

  const titleValue = titleInput.value.trim();

  if (!titleValue) {
    titleError.textContent = "Title is required.";
    titleError.hidden = false;
    titleInput.setAttribute("aria-invalid", "true");
    return;
  }

  // Valid — clear any previous error state
  titleError.hidden = true;
  titleInput.removeAttribute("aria-invalid");

  handleAdd({
    title: titleValue,
    due_date: dueDateInput.value.trim() || null,
    priority: priorityInput.value,
    project_id: PROJECT_ID,
  });

  form.reset();
  priorityInput.value = "medium";
});

// Clear the error as soon as the field becomes valid again (Task 13)
titleInput.addEventListener("input", () => {
  if (titleInput.value.trim()) {
    titleError.hidden = true;
    titleInput.removeAttribute("aria-invalid");
  }
});

// ---------------------------------------------------------------------------
// Init: render cached copy immediately, then kick off the live fetch
// (Task 14 — the page never shows a blank list while data loads).
// ---------------------------------------------------------------------------
function init() {
  const cached = readCache();
  if (cached.length) {
    renderTasks(cached);
  }
  loadTasks();
}

init();
