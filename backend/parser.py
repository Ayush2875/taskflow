"""
parser.py
---------
The required, keyless, deterministic mock parser (Section 3, Task 3).
Simulates what an LLM's structured response would contain, following the
brief's algorithm EXACTLY so any two correct implementations produce
identical output for the same input. No network calls, no API keys.

mock_parse(description) -> {"title": str, "priority": str, "due_date_hint": str|None}
"""

import re

# Step (b): priority keyword groups, checked in this exact order.
# Group (i) beats group (ii) if both are present.
GROUP_I_KEYWORDS = ["urgent", "asap"]              # -> priority = "high"
GROUP_II_KEYWORDS = ["whenever", "low priority"]   # -> priority = "low"

# Step (c): due-date keywords, checked in this exact order — first match wins.
SIMPLE_DATE_KEYWORDS = ["today", "tomorrow", "next week"]
NEXT_WEEKDAY_PHRASES = [
    "next monday", "next tuesday", "next wednesday", "next thursday",
    "next friday", "next saturday", "next sunday",
]
BARE_WEEKDAYS = [
    "monday", "tuesday", "wednesday", "thursday",
    "friday", "saturday", "sunday",
]


def mock_parse(description):
    lower_desc = description.lower()  # (a) lower-cased copy for matching only

    # --- (b) Priority ---
    group_i_found = [kw for kw in GROUP_I_KEYWORDS if kw in lower_desc]
    group_ii_found = [kw for kw in GROUP_II_KEYWORDS if kw in lower_desc]

    if group_i_found:
        priority = "high"
    elif group_ii_found:
        priority = "low"
    else:
        priority = "medium"

    # Title-stripping note: strip EVERY matched group (i)/(ii) keyword found
    # anywhere, not just the one that decided priority.
    priority_keywords_to_strip = group_i_found + group_ii_found

    # --- (c) Due-date hint — first match wins, checked in exact order ---
    due_date_hint = None
    matched_date_phrase = None

    for kw in SIMPLE_DATE_KEYWORDS:
        if kw in lower_desc:
            due_date_hint = kw
            matched_date_phrase = kw
            break

    if due_date_hint is None:
        for phrase in NEXT_WEEKDAY_PHRASES:
            if phrase in lower_desc:
                due_date_hint = phrase
                matched_date_phrase = phrase
                break

    if due_date_hint is None:
        for day in BARE_WEEKDAYS:
            if day in lower_desc:
                due_date_hint = day
                matched_date_phrase = day
                break

    # --- (d) Title — start from the ORIGINAL-cased description, remove only
    # the exact spans that matched above ---
    title = description
    for kw in priority_keywords_to_strip:
        title = re.sub(re.escape(kw), "", title, flags=re.IGNORECASE)
    if matched_date_phrase:
        title = re.sub(re.escape(matched_date_phrase), "", title, flags=re.IGNORECASE)

    # Collapse whitespace left behind by removed spans, then strip ends.
    title = re.sub(r"\s+", " ", title).strip()

    if not title:
        title = "Untitled task"

    return {"title": title, "priority": priority, "due_date_hint": due_date_hint}


# ---------------------------------------------------------------------------
# Verify against the brief's 4 worked examples exactly, before this ever
# touches the API.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    cases = [
        (
            "This is urgent, mark it ASAP please",
            {"title": "This is , mark it please", "priority": "high", "due_date_hint": None},
        ),
        (
            "   ",
            {"title": "Untitled task", "priority": "medium", "due_date_hint": None},
        ),
        (
            "Finish the report next Friday, it's urgent",
            {"title": "Finish the report , it's", "priority": "high", "due_date_hint": "next friday"},
        ),
        (
            "tomorrow review tomorrow",
            {"title": "review", "priority": "medium", "due_date_hint": "tomorrow"},
        ),
    ]

    for i, (description, expected) in enumerate(cases, start=1):
        result = mock_parse(description)
        status = "PASS" if result == expected else "FAIL"
        print(f"{status}: worked example {i}")
        print(f"    input:    {description!r}")
        print(f"    expected: {expected}")
        print(f"    got:      {result}")
        if status == "FAIL":
            raise SystemExit(f"Worked example {i} did not match — fix before continuing.")

    print("\nAll 4 worked examples match exactly.")
