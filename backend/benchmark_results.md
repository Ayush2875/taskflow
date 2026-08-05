# TaskFlow — Algorithm Benchmark Results

Raw comparison counts from `benchmark.py`, run against synthetic task data shaped like the real `title`/`priority`/`due_date` fields the app's endpoints use.

```
  Size |  insertion_sort |  binary(present) |  binary(absent) |  linear(present) |  linear(absent)
--------------------------------------------------------------------------------------------------
    10 |              29 |                4 |               3 |                4 |              10
   500 |           63132 |                9 |               9 |              326 |             500
  3000 |         2246602 |               12 |              11 |             1195 |            3000
```
