def insertion_sort(records, key):
    """
    Sort `records` in place by record[key], ascending.
    Standard insertion sort: starting from the second element, compare
    backwards and shift larger elements right until we find the correct
    slot for the current element.
    Mutates records directly. No return value.
    """
    for i in range(1, len(records)):
        current = records[i]
        current_value = current[key]
        j = i - 1
        # Shift everything bigger than current_value one slot to the right
        while j >= 0 and records[j][key] > current_value:
            records[j + 1] = records[j]
            j -= 1
        records[j + 1] = current


def binary_search(sorted_records, target_value, key):
    """
    sorted_records MUST already be sorted ascending by key (e.g. via
    insertion_sort above) — binary search only works on sorted data.
    Returns the index of the first record where record[key] == target_value,
    or -1 if no such record exists.
    """
    low = 0
    high = len(sorted_records) - 1

    while low <= high:
        mid = (low + high) // 2
        mid_value = sorted_records[mid][key]

        if mid_value == target_value:
            return mid
        elif mid_value < target_value:
            low = mid + 1
        else:
            high = mid - 1

    return -1


def linear_search(records, target_value, key):
    """
    Baseline search: scan every record in order, no sorting required.
    Returns the index of the first match, or -1 if absent.
    """
    for i, record in enumerate(records):
        if record[key] == target_value:
            return i
    return -1


# ---------------------------------------------------------------------------
# Comparison-counting wrappers — same logic as the three functions above,
# reimplemented so we can count exactly how many key-comparisons each one
# performs. Used for the Task 5 benchmark (10 / 500 / 3000 records) and the
# README's complexity write-up. Signatures/return contracts of the ORIGINAL
# functions above are untouched — these are separate functions.
# ---------------------------------------------------------------------------

def insertion_sort_count(records, key):
    """
    Sorts records in place exactly like insertion_sort, but also counts
    every comparison made (records[j][key] > current_value). Returns only
    that integer count.
    """
    comparisons = 0
    for i in range(1, len(records)):
        current = records[i]
        current_value = current[key]
        j = i - 1
        while j >= 0:
            comparisons += 1
            if records[j][key] > current_value:
                records[j + 1] = records[j]
                j -= 1
            else:
                break
        records[j + 1] = current
    return comparisons


def binary_search_count(sorted_records, target_value, key):
    """
    Same logic as binary_search, but also counts comparisons.
    Returns {"index": ..., "comparison_count": ...}.
    """
    low = 0
    high = len(sorted_records) - 1
    comparisons = 0

    while low <= high:
        mid = (low + high) // 2
        mid_value = sorted_records[mid][key]
        comparisons += 1

        if mid_value == target_value:
            return {"index": mid, "comparison_count": comparisons}
        elif mid_value < target_value:
            low = mid + 1
        else:
            high = mid - 1

    return {"index": -1, "comparison_count": comparisons}


def linear_search_count(records, target_value, key):
    """
    Same logic as linear_search, but also counts comparisons.
    Returns {"index": ..., "comparison_count": ...}.
    Note: on an absent target, comparison_count will equal len(records),
    since every record gets checked exactly once.
    """
    comparisons = 0
    for i, record in enumerate(records):
        comparisons += 1
        if record[key] == target_value:
            return {"index": i, "comparison_count": comparisons}
    return {"index": -1, "comparison_count": comparisons}


# ---------------------------------------------------------------------------
# Quick manual sanity check — run this file directly to eyeball correctness
# before wiring it into the API. Not the official Task 7 checks script
# (that's a separate file, check_algorithms.py, added later).
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    data = [
        {"id": 3, "title": "C task", "priority_rank": 2},
        {"id": 1, "title": "A task", "priority_rank": 3},
        {"id": 2, "title": "B task", "priority_rank": 1},
    ]

    insertion_sort(data, "priority_rank")
    print("Sorted by priority_rank:", [d["priority_rank"] for d in data])
    assert [d["priority_rank"] for d in data] == [1, 2, 3], "insertion_sort failed"

    idx = binary_search(data, 3, "priority_rank")
    print("binary_search for 3 ->", idx, "(expect last index, 2)")
    assert idx == 2

    idx = binary_search(data, 99, "priority_rank")
    print("binary_search for missing value ->", idx, "(expect -1)")
    assert idx == -1

    idx = linear_search(data, 1, "priority_rank")
    print("linear_search for 1 ->", idx, "(expect first index, 0)")
    assert idx == 0

    print("All manual checks passed.")

    # --- counting wrappers ---
    data2 = [
        {"id": 3, "priority_rank": 2},
        {"id": 1, "priority_rank": 3},
        {"id": 2, "priority_rank": 1},
    ]
    count = insertion_sort_count(data2, "priority_rank")
    print("insertion_sort_count comparisons:", count, "(expect > 0, int)")
    assert isinstance(count, int) and count > 0
    assert [d["priority_rank"] for d in data2] == [1, 2, 3]

    result = binary_search_count(data2, 3, "priority_rank")
    print("binary_search_count for 3 ->", result)
    assert result["index"] == 2 and result["comparison_count"] > 0

    result = linear_search_count(data2, 99, "priority_rank")
    print("linear_search_count for missing value ->", result)
    assert result["index"] == -1 and result["comparison_count"] == len(data2)

    print("All counting-wrapper checks passed.")