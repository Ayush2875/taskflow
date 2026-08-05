## Section 2 — Algorithms: Complexity & Benchmark Analysis

### Time complexity

| Function | Best case | Worst case |
|---|---|---|
| `insertion_sort` | O(n) — already sorted | O(n²) — reverse sorted / random |
| `binary_search` | O(1) — target at midpoint | O(log n) |
| `linear_search` | O(1) — target at first index | O(n) — target absent or at the end |

### Benchmark evidence

Raw comparison counts from `benchmark.py` (see `benchmark_results.md` for the full table), run against synthetic task data shaped like the real `title`/`priority`/`due_date` fields:

| Size | insertion_sort | binary_search | linear_search (absent) |
|---|---|---|---|
| 10 | 29 | 4 | 10 |
| 500 | 63,132 | 9 | 500 |
| 3,000 | 2,246,602 | 12 | 3,000 |

### Is sorting first worth it?

Sorting via `insertion_sort` is expensive relative to searching — at 3,000 tasks it takes over 2.2 million comparisons, growing roughly quadratically with size, while `binary_search` only needs about 12 comparisons per lookup regardless of scale (log₂3000 ≈ 11.5). Given how TaskFlow is actually used — a team lists and sorts their tasks repeatedly through the day, but adds or renames tasks comparatively rarely — the sort cost is paid once per view, then every subsequent search against that sorted view is nearly free by comparison. If tasks were instead searched with `linear_search`, every lookup would cost up to O(n) comparisons regardless of how many searches follow, which is worse than paying the sort cost once and reusing it. The tradeoff would flip only if edits (adds/renames) happened far more often than reads, since each edit could require re-sorting — but that's not this app's usage pattern.

