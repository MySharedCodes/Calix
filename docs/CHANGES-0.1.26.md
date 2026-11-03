# Calix 0.1.26

AI clients can finish `eval` or `run` with `--open-ui`. Calix saves a new
notebook containing inputs, computed outputs and errors, then opens it in the
desktop. Original notebooks are preserved; later cells remain present if a
calculation fails. Desktop kernels start fresh and saved outputs are marked
stale. `open-ui --notebook PATH` and authenticated `POST /api/open-ui` also
support existing notebooks.

The installation includes AGENTS.md, AI-CONTROL.md and API.md for unfamiliar
agents. The native launcher preserves Windows expression arguments. Desktop
builds now rebuild the frozen service first, preventing CLI/UI version drift.

The local DeepSeek Harness comparison records fresh sessions, raw tool calls
and total task duration. Results and experimental limitations are distributed
separately with the benchmark report.
