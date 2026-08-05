"""
check_algorithms.py
--------------------
Task 7's required checks script — plain if/else, no assert/pytest/unittest.
Run with:
    python3 check_algorithms.py

Prints one PASS/FAIL line per case. Completes normally either way (no
unhandled exception) even if something fails.
"""

from algorithms import (
    insertion_sort,
    binary_search,
    linear_search,
    insertion_sort_count,
    binary_search_count,
    linear_search_count,
)


def check(case_name, result, expected):
    if result == expected:
        print(f"PASS: {case_name}")
    else:
        print(f"FAIL: {case_name} — expected {expected}, got {result}")


def run_all_checks():
    # --- insertion_sort on an empty list ---
    empty = []
    insertion_sort(empty, "key")
    check("insertion_sort on empty list stays empty", empty, [])

    # --- insertion_sort on a single-element list ---
    single = [{"key": 5}]
    insertion_sort(single, "key")
    check("insertion_sort on single-element list unchanged", single, [{"key": 5}])

    # --- binary_search: first, last, middle of a sorted list ---
    sorted_data = [{"key": 10}, {"key": 20}, {"key": 30}, {"key": 40}, {"key": 50}]
    check("binary_search finds value at first index", binary_search(sorted_data, 10, "key"), 0)
    check("binary_search finds value at last index", binary_search(sorted_data, 50, "key"), 4)
    check("binary_search finds value at middle index", binary_search(sorted_data, 30, "key"), 2)

    # --- binary_search: not-found case ---
    check("binary_search returns -1 when target absent", binary_search(sorted_data, 999, "key"), -1)

    # --- insertion_sort_count: correctness + return type ---
    count_data = [{"key": 3}, {"key": 1}, {"key": 2}]
    comparisons = insertion_sort_count(count_data, "key")
    check("insertion_sort_count leaves list correctly sorted",
          [d["key"] for d in count_data], [1, 2, 3])
    check("insertion_sort_count returns a plain int > 0",
          (type(comparisons) == int and comparisons > 0), True)

    # --- binary_search_count: index + comparison_count ---
    sorted_for_binary = [{"key": 10}, {"key": 20}, {"key": 30}, {"key": 40}, {"key": 50}]
    expected_index = 2  # key 30 is at index 2
    result = binary_search_count(sorted_for_binary, 30, "key")
    check("binary_search_count finds correct index",
          result["index"], expected_index)
    check("binary_search_count comparison_count is int > 0",
          (type(result["comparison_count"]) == int and result["comparison_count"] > 0), True)

    # --- linear_search_count: absent value ---
    linear_data = [{"key": 1}, {"key": 2}, {"key": 3}, {"key": 4}]
    result = linear_search_count(linear_data, 999, "key")
    check("linear_search_count returns -1 index for absent value",
          result["index"], -1)
    check("linear_search_count comparison_count equals list length for absent value",
          result["comparison_count"], len(linear_data))


if __name__ == "__main__":
    run_all_checks()
