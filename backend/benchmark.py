"""
benchmark.py
------------
Runs the Section 2 counting-wrapper functions (insertion_sort_count,
binary_search_count, linear_search_count) against synthetic task data at
three sizes (10, 500, 3000) — the same sizes and shape the real
GET /tasks?sort= and GET /tasks/search endpoints operate on.

Run with:
    python3 benchmark.py

Prints a results table to the console AND writes the raw numbers to
benchmark_results.md so they're committed to the repo (not just a verbal
claim), per the Task 5 requirement.
"""

from algorithms import insertion_sort_count, binary_search_count, linear_search_count
from seed import generate_tasks

SIZES = [10, 500, 3000]


def run_benchmark():
    results = []

    for size in SIZES:
        tasks = generate_tasks(size)

        # --- Sorting benchmark: sort a fresh copy by title ---
        sort_copy = [dict(t) for t in tasks]
        sort_comparisons = insertion_sort_count(sort_copy, "title")

        # --- Search benchmarks ---
        # Present-target case: search for the last title in the now-sorted
        # list — a reasonable worst-case-ish probe for linear_search, while
        # still O(log n) for binary_search.
        present_target = sort_copy[-1]["title"]
        # Absent-target case: guaranteed not to exist in generated data.
        absent_target = "NOT_A_REAL_TASK_TITLE_XYZ"

        unsorted_copy = [dict(t) for t in tasks]  # unsorted, for linear_search

        binary_present = binary_search_count(sort_copy, present_target, "title")
        binary_absent = binary_search_count(sort_copy, absent_target, "title")
        linear_present = linear_search_count(unsorted_copy, present_target, "title")
        linear_absent = linear_search_count(unsorted_copy, absent_target, "title")

        results.append({
            "size": size,
            "insertion_sort_comparisons": sort_comparisons,
            "binary_search_present_comparisons": binary_present["comparison_count"],
            "binary_search_absent_comparisons": binary_absent["comparison_count"],
            "linear_search_present_comparisons": linear_present["comparison_count"],
            "linear_search_absent_comparisons": linear_absent["comparison_count"],
        })

    return results


def print_and_save(results):
    lines = []
    header = f"{'Size':>6} | {'insertion_sort':>15} | {'binary(present)':>16} | {'binary(absent)':>15} | {'linear(present)':>16} | {'linear(absent)':>15}"
    sep = "-" * len(header)
    lines.append(header)
    lines.append(sep)

    for r in results:
        row = (
            f"{r['size']:>6} | {r['insertion_sort_comparisons']:>15} | "
            f"{r['binary_search_present_comparisons']:>16} | {r['binary_search_absent_comparisons']:>15} | "
            f"{r['linear_search_present_comparisons']:>16} | {r['linear_search_absent_comparisons']:>15}"
        )
        lines.append(row)

    table_text = "\n".join(lines)
    print(table_text)

    with open("benchmark_results.md", "w") as f:
        f.write("# TaskFlow — Algorithm Benchmark Results\n\n")
        f.write("Raw comparison counts from `benchmark.py`, run against synthetic ")
        f.write("task data shaped like the real `title`/`priority`/`due_date` fields ")
        f.write("the app's endpoints use.\n\n")
        f.write("```\n")
        f.write(table_text)
        f.write("\n```\n")

    print("\nSaved raw results to benchmark_results.md")


if __name__ == "__main__":
    results = run_benchmark()
    print_and_save(results)
