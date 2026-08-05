"""
seed.py
-------
Generates synthetic in-memory task dictionaries — same fields the real
endpoints operate on (title, priority, due_date) — at three sizes, so the
benchmark in benchmark.py can measure the counting-wrapper functions
against realistically-shaped data without needing to actually insert
thousands of rows into the database.

This satisfies Section 2 Task 5's "synthetic in-memory task dictionaries
... at the same three sizes" option. If you'd rather seed the real DB
instead, you can adapt generate_tasks() below to POST to /tasks in a loop
— the shape of the data is identical either way.
"""

import random

PRIORITIES = ["low", "medium", "high"]
DUE_DATE_PHRASES = ["today", "tomorrow", "next week", "next friday", None]


def generate_tasks(count, seed=42):
    """
    Returns a list of `count` synthetic task dicts shaped exactly like the
    real Task rows the API works with: id, title, priority, due_date.
    A fixed seed makes benchmark runs reproducible.
    """
    rng = random.Random(seed)
    verbs = ["Restock", "Audit", "Clean", "Label", "Inspect", "Repack", "Sort", "Count", "Move", "Check"]
    nouns = ["chiller", "aisle", "dock", "shelf", "crate", "bin", "counter", "freezer", "rack", "gate"]

    tasks = []
    for i in range(1, count + 1):
        # A random 6-digit suffix (not the sequential id) keeps titles from
        # being lexically pre-sorted by construction — otherwise
        # insertion_sort would always hit its best case, which would give a
        # misleadingly flat/linear benchmark instead of realistic average-
        # case behavior.
        random_suffix = rng.randint(100000, 999999)
        title = f"{rng.choice(verbs)} {rng.choice(nouns)} {random_suffix}"
        tasks.append({
            "id": i,
            "title": title,
            "priority": rng.choice(PRIORITIES),
            "due_date": rng.choice(DUE_DATE_PHRASES),
        })
    return tasks


if __name__ == "__main__":
    for size in (10, 500, 3000):
        sample = generate_tasks(size)
        print(f"Generated {len(sample)} tasks, e.g. {sample[0]}")
