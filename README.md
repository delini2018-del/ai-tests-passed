# 181,711 Tests Passed. Nobody Read the Code. What Could the AI Be Hiding?

Code for the Medium article. A dependency-free mutation tester plants one small bug at a time in two
well-tested Python libraries and runs each project's own tests.

| Result | humanize | more-itertools (recipes) |
|---|---|---|
| Line coverage of mutated code | 98–100% | 99% |
| Tests (official suite) | 841 | 199 + 9,884 sub-tests |
| Planted bugs | 531 (all sites) | 91 (random sample) |
| Caught by at least one test | 475 (89%) | 68 (75%) |
| Survivors shown to change visible output | 14 of 56 | not analysed |

Example escapes that pass all 841 humanize tests: 60 s shown as "60 seconds" instead of "a minute";
1,000 µs shown as "a moment" instead of "1 millisecond"; scientific notation crashing on 1e33.

`results/` holds every mutant's verdict; `python survivors.py humanize libs/humanize` prints each survivor.
Licence: MIT. Note: configs paths assume libs/ is cloned as in run_all.sh.
