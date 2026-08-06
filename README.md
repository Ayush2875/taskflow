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

## Section 3 — AI Quick-Add: Prompting Rationale & Worked Example

Prompting technique rationale
+
The system message and mock parser are modeled on a zero-shot, rule-based extraction approach rather than few-shot or chain-of-thought. The system message states the extraction task directly — pull out title, priority, and due_date_hint from free text — without providing example input/output pairs (few-shot) or asking the model to reason step-by-step before answering (chain-of-thought).

This choice fits the task well: the fields being extracted follow a small, fixed set of surface-level keyword rules (a handful of priority and date-phrase keywords), not a task requiring nuanced judgment or multi-step reasoning. A zero-shot instruction is enough to specify the what; it doesn't need worked examples to specify the how, since the parsing logic is closed-form rather than open-ended.

This matters for token usage and reliability: few-shot prompting would mean shipping several example conversations in every request just to anchor the model's behavior, multiplying token cost on every call for marginal gain here. Chain-of-thought would add reasoning tokens and, more importantly, non-determinism — an LLM "thinking out loud" through keyword matching could phrase its extraction differently each run, which is exactly what this feature can't tolerate (the brief requires the mock to be deterministic, so any two correct implementations produce identical output for the same input). A tightly-scoped zero-shot instruction keeps the request cheap and keeps output shape predictable, which is also why the mock parser mirrors it faithfully with hand-coded rules rather than any probabilistic behavior — the system prompt and the mock are meant to produce the same structured result every time, by design.

Five worked examples
#	Input	Output
1	"Please water the plants whenever you get a chance"	{"title": "Please water the plants you get a chance", "priority": "low", "due_date_hint": null}
2	"Submit the invoice today, low priority though"	{"title": "Submit the invoice , though", "priority": "low", "due_date_hint": "today"}
3	"Call the vendor next Monday urgent"	{"title": "Call the vendor", "priority": "high", "due_date_hint": "next monday"}
4	"Clean the warehouse floor"	{"title": "Clean the warehouse floor", "priority": "medium", "due_date_hint": null}
5	"asap fix the broken freezer door next week"	{"title": "fix the broken freezer door", "priority": "high", "due_date_hint": "next week"}