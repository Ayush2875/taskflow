/**
 * script.js — TaskFlow dashboard
 * ------------------------------
 * Talks to the FastAPI backend over Fetch. Reads (GET) are public; writes
 * (create/edit/delete) need a JWT, which we get from POST /auth/login and
 * send as "Authorization: Bearer <token>".
 *
 * Rendering rule (unchanged): DOM nodes are built with createElement and
 * user-provided text is set with textContent, never innerHTML.
 *
 * Token storage: localStorage. That's convenient (survives reloads) but any
 * script running on the page could read it, which is exactly why we never
 * put user text into innerHTML. Production apps often prefer an HttpOnly
 * cookie instead.
 */

const API_BASE = "https://taskflow-api-olqz.onrender.com";
const TOKEN_KEY = "taskflow_token";
const USER_KEY = "taskflow_user";
const CACHE_KEY = "taskflow_task_cache";

let projectId = null;      // resolved from the backend, not hardcoded
let currentTasks = [];
let authMode = "login";    // "login" | "register"
let noticeTimer = null;

// --- DOM references --------------------------------------------------------
const taskForm = document.getElementById("task-form");
const titleInput = document.getElementById("title");
const dueDateInput = document.getElementById("due_date");
const priorityInput = document.getElementById("priority");
const titleError = document.getElementById("title-error");
const taskList = document.getElementById("task-list");
const taskCount = document.getElementById("task-count");
const emptyState = document.getElementById("empty-state");
const connectionStatus = document.getElementById("connection-status");
const notice = document.getElementById("notice");

const authPanel = document.getElementById("auth-panel");
const authForm = document.getElementById("auth-form");
const authHeading = document.getElementById("auth-heading");
const authError = document.getElementById("auth-error");
const authSubmit = document.getElementById("auth-submit");
const nameField = document.getElementById("name-field");
const nameInput = document.getElementById("auth-name");
const emailInput = document.getElementById("auth-email");
const passwordInput = document.getElementById("auth-password");
const tabLogin = document.getElementById("tab-login");
const tabRegister = document.getElementById("tab-register");
const intake = document.getElementById("intake");
const userChip = document.getElementById("user-chip");
const logoutBtn = document.getElementById("logout-btn");

// ---------------------------------------------------------------------------
// Storage helpers — every access is wrapped, because storage can be blocked
// or full, and the page must keep working either way.
// ---------------------------------------------------------------------------
function storageGet(key) {
  try { return localStorage.getItem(key); } catch (err) { return null; }
}
function storageSet(key, value) {
  try { localStorage.setItem(key, value); } catch (err) { /* ignore */ }
}
function storageRemove(key) {
  try { localStorage.removeItem(key); } catch (err) { /* ignore */ }
}

function readCache() {
  try {
    const raw = storageGet(CACHE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (err) {
    return [];
  }
}
function writeCache(tasks) {
  storageSet(CACHE_KEY, JSON.stringify(tasks));
}

// ---------------------------------------------------------------------------
// Session helpers
// ---------------------------------------------------------------------------
function getToken() { return storageGet(TOKEN_KEY); }
function isLoggedIn() { return Boolean(getToken()); }

function getUser() {
  try {
    const raw = storageGet(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (err) {
    return null;
  }
}

function saveSession(token, user) {
  storageSet(TOKEN_KEY, token);
  storageSet(USER_KEY, JSON.stringify(user));
}

function clearSession() {
  storageRemove(TOKEN_KEY);
  storageRemove(USER_KEY);
}

// Reads the "sub" (user id) claim out of the JWT so we know our own id.
// This is only for convenience — the browser can't verify the signature,
// and the SERVER never trusts anything the client says about who it is.
function decodeJwtPayload(token) {
  try {
    let b64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    while (b64.length % 4) b64 += "=";
    return JSON.parse(atob(b64));
  } catch (err) {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Small UI helpers
// ---------------------------------------------------------------------------
function showNotice(message, isError) {
  notice.textContent = message;
  notice.className = isError ? "notice error" : "notice";
  notice.hidden = false;
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => { notice.hidden = true; }, 6000);
}

function setStatus(online) {
  connectionStatus.textContent = online ? "live" : "offline — showing cached data";
  connectionStatus.className = online ? "header-status online" : "header-status offline";
}

// Turns a failed response into a readable sentence. FastAPI sends either
// {"detail": "text"} or {"detail": [{"msg": "..."}]} for validation errors.
async function errorMessage(res) {
  try {
    const body = await res.json();
    const detail = body.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length) {
      return String(detail[0].msg || "Invalid input").replace(/^Value error, /, "");
    }
  } catch (err) { /* fall through */ }
  return `Request failed (${res.status})`;
}

// ---------------------------------------------------------------------------
// API wrapper. With { auth: true } it attaches the Bearer token, and if the
// server answers 401 (expired/invalid token) it logs the user out cleanly.
// ---------------------------------------------------------------------------
async function apiFetch(path, options, flags) {
  const opts = options || {};
  const useAuth = Boolean(flags && flags.auth);
  const headers = Object.assign({}, opts.headers);
  if (opts.body) headers["Content-Type"] = "application/json";
  if (useAuth && getToken()) headers["Authorization"] = `Bearer ${getToken()}`;

  const res = await fetch(`${API_BASE}${path}`, Object.assign({}, opts, { headers }));

  if (useAuth && res.status === 401) {
    clearSession();
    updateAuthUI();
    showNotice("Your session expired — please log in again.", true);
  }
  return res;
}

// ---------------------------------------------------------------------------
// Auth UI
// ---------------------------------------------------------------------------
function updateAuthUI() {
  const loggedIn = isLoggedIn();
  const user = getUser();

  authPanel.hidden = loggedIn;
  intake.hidden = !loggedIn;
  logoutBtn.hidden = !loggedIn;
  userChip.hidden = !loggedIn;
  userChip.textContent = loggedIn ? (user && user.email ? user.email : "signed in") : "";

  // Edit/Delete buttons only exist while logged in, so re-render.
  renderTasks(currentTasks);
}

function clearAuthError() {
  authError.hidden = true;
  authError.textContent = "";
  [nameInput, emailInput, passwordInput].forEach((el) => el.removeAttribute("aria-invalid"));
}

function showAuthError(message, invalidInput) {
  authError.textContent = message;
  authError.hidden = false;
  if (invalidInput) invalidInput.setAttribute("aria-invalid", "true");
}

function setAuthMode(mode) {
  authMode = mode;
  const isRegister = mode === "register";
  nameField.hidden = !isRegister;
  authHeading.textContent = isRegister ? "Create an account" : "Log in to add or edit tickets";
  authSubmit.textContent = isRegister ? "Register" : "Log in";
  tabLogin.classList.toggle("active", !isRegister);
  tabRegister.classList.toggle("active", isRegister);
  passwordInput.setAttribute("autocomplete", isRegister ? "new-password" : "current-password");
  clearAuthError();
}

tabLogin.addEventListener("click", () => setAuthMode("login"));
tabRegister.addEventListener("click", () => setAuthMode("register"));

authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearAuthError();

  const name = nameInput.value.trim();
  const email = emailInput.value.trim();
  const password = passwordInput.value;
  const isRegister = authMode === "register";

  // Client-side validation (the server validates again — never trust the client)
  if (isRegister && !name) { showAuthError("Name is required.", nameInput); return; }
  if (!email) { showAuthError("Email is required.", emailInput); return; }
  if (!password) { showAuthError("Password is required.", passwordInput); return; }
  if (isRegister && password.length < 8) {
    showAuthError("Password must be at least 8 characters.", passwordInput);
    return;
  }

  authSubmit.disabled = true;
  try {
    if (isRegister) {
      const reg = await apiFetch("/users", {
        method: "POST",
        body: JSON.stringify({ name, email, password }),
      });
      if (!reg.ok) { showAuthError(await errorMessage(reg)); return; }
    }

    const login = await apiFetch("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    if (!login.ok) { showAuthError(await errorMessage(login)); return; }

    const data = await login.json();
    const payload = decodeJwtPayload(data.access_token);
    saveSession(data.access_token, { id: payload ? Number(payload.sub) : null, email });

    authForm.reset();
    setAuthMode("login");   // next time the panel appears, start on "Log in"
    updateAuthUI();
    showNotice(isRegister ? "Account created — you're logged in." : "Logged in.", false);
    await loadTasks();
  } catch (err) {
    showAuthError("Could not reach the server. Is the backend running?");
  } finally {
    authSubmit.disabled = false;
  }
});

logoutBtn.addEventListener("click", () => {
  clearSession();
  setAuthMode("login");
  updateAuthUI();
  showNotice("Logged out.", false);
});

// ---------------------------------------------------------------------------
// Rendering — createElement / appendChild / textContent only
// ---------------------------------------------------------------------------
function emptyMessage() {
  if (projectId === null) {
    return isLoggedIn() ? "No project available yet." : "No project yet — log in to create one.";
  }
  return isLoggedIn() ? "No tickets yet — add one above." : "No tickets yet — log in to add one.";
}

function renderTasks(tasks) {
  taskList.innerHTML = ""; // clearing our own container is fine; user values never go through innerHTML

  if (!tasks.length) {
    emptyState.textContent = emptyMessage();
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
  title.textContent = task.title;

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
  item.appendChild(main);

  // Edit/Delete need a token, so logged-out visitors don't get the buttons.
  if (isLoggedIn()) {
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
    item.appendChild(actions);
  }

  return item;
}

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
  cancelBtn.addEventListener("click", () => renderTasks(currentTasks));

  editRow.appendChild(dueField);
  editRow.appendChild(priorityField);
  editRow.appendChild(saveBtn);
  editRow.appendChild(cancelBtn);

  item.appendChild(titleField);
  item.appendChild(editRow);
}

// ---------------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------------

// Picks which project the dashboard shows. Uses the first project that
// exists; if there are none and we're logged in, creates one owned by us.
// (Replaces the old hardcoded PROJECT_ID = 1, which broke on a fresh DB.)
async function resolveProject() {
  const res = await apiFetch("/projects");
  if (!res.ok) throw new Error(`GET /projects failed: ${res.status}`);
  const projects = await res.json();

  if (projects.length) {
    projectId = projects[0].id;
    return;
  }

  const user = getUser();
  if (isLoggedIn() && user && user.id) {
    const created = await apiFetch(
      "/projects",
      { method: "POST", body: JSON.stringify({ name: "Dark Store Ops", owner_id: user.id }) },
      { auth: true }
    );
    if (created.ok) {
      projectId = (await created.json()).id;
      return;
    }
  }
  projectId = null;
}

async function loadTasks() {
  try {
    if (projectId === null) await resolveProject();

    const res = await apiFetch("/tasks");
    if (!res.ok) throw new Error(`GET /tasks failed: ${res.status}`);
    const allTasks = await res.json();

    currentTasks = projectId === null ? [] : allTasks.filter((t) => t.project_id === projectId);
    setStatus(true);
    renderTasks(currentTasks);
    writeCache(currentTasks);
  } catch (err) {
    console.error(err);
    setStatus(false);
    // The cached copy was already rendered by init(), so nothing else to do.
  }
}

// ---------------------------------------------------------------------------
// Write operations (all need a token)
// ---------------------------------------------------------------------------
async function sendWrite(path, method, body, failureText) {
  try {
    const res = await apiFetch(
      path,
      { method, body: body ? JSON.stringify(body) : undefined },
      { auth: true }
    );
    if (res.status === 401) return false; // apiFetch already logged us out + showed a notice
    if (!res.ok) {
      showNotice(await errorMessage(res), true);
      return false;
    }
    await loadTasks();
    return true;
  } catch (err) {
    console.error(err);
    showNotice(`${failureText} — check that the backend is running.`, true);
    return false;
  }
}

function handleAdd(taskData) { return sendWrite("/tasks", "POST", taskData, "Could not add task"); }
function handleUpdate(id, updates) { return sendWrite(`/tasks/${id}`, "PUT", updates, "Could not update task"); }
function handleDelete(id) { return sendWrite(`/tasks/${id}`, "DELETE", null, "Could not delete task"); }

// ---------------------------------------------------------------------------
// Add-task form: preventDefault + client-side validation
// ---------------------------------------------------------------------------
taskForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const titleValue = titleInput.value.trim();

  if (!titleValue) {
    titleError.textContent = "Title is required.";
    titleError.hidden = false;
    titleInput.setAttribute("aria-invalid", "true");
    return;
  }

  titleError.hidden = true;
  titleInput.removeAttribute("aria-invalid");

  if (projectId === null) {
    showNotice("No project available yet — reload the page.", true);
    return;
  }

  const ok = await handleAdd({
    title: titleValue,
    due_date: dueDateInput.value.trim() || null,
    priority: priorityInput.value,
    project_id: projectId,
  });

  if (ok) {
    taskForm.reset();
    priorityInput.value = "medium";
  }
});

titleInput.addEventListener("input", () => {
  if (titleInput.value.trim()) {
    titleError.hidden = true;
    titleInput.removeAttribute("aria-invalid");
  }
});

// ---------------------------------------------------------------------------
// Init: show the cached list immediately, then fetch the live one.
// ---------------------------------------------------------------------------
function init() {
  currentTasks = readCache();
  setAuthMode("login");
  updateAuthUI();   // also renders currentTasks
  loadTasks();
}

init();
