"""
real_llm.py
-----------
OPTIONAL enhancement (Section 3, Task 4) -- layered on top of the required
mock parser in parser.py, never a replacement for it.

This uses a LOCAL, FREE model served by Ollama (https://ollama.com, open
source). No API key, no account, no paid service, nothing leaves your
machine. It only runs when USE_REAL_LLM=true. If Ollama isn't installed or
running, or the model returns something unusable, this raises and the
caller in main.py falls back to parser.mock_parse() automatically.

Standard library only (urllib) -- no extra dependency to install.

Optional environment variables:
    OLLAMA_HOST   default http://localhost:11434
    OLLAMA_MODEL  default llama3.2   (install with: ollama pull llama3.2)
"""

import json
import os
import urllib.request

SYSTEM_PROMPT = (
    "You are a task-parsing assistant. Given a free-text task description, "
    "extract a structured task. Respond with ONLY a JSON object, no other "
    "text, in exactly this shape: "
    '{"title": "<description with priority/date keywords removed, trimmed>", '
    '"priority": "<low|medium|high>", '
    '"due_date_hint": "<lowercase date phrase, or null if none>"}'
)


def call_real_llm(description: str) -> dict:
    """
    Returns the same shape as parser.mock_parse():
    {"title", "priority", "due_date_hint"}.
    Raises on ANY failure (Ollama not running, timeout, bad JSON, missing
    fields, invalid priority) -- the caller decides to fall back to the mock.
    """
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    model = os.environ.get("OLLAMA_MODEL", "llama3.2")

    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": description},
        ],
        "stream": False,
        "format": "json",  # asks Ollama to constrain output to valid JSON
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{host}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    parsed = json.loads(payload["message"]["content"])

    for field in ("title", "priority", "due_date_hint"):
        if field not in parsed:
            raise ValueError(f"LLM response missing field: {field}")

    if parsed["priority"] not in ("low", "medium", "high"):
        raise ValueError(f"LLM returned invalid priority: {parsed['priority']}")

    if not isinstance(parsed["title"], str) or not parsed["title"].strip():
        parsed["title"] = "Untitled task"

    return parsed
