# Calix agent workflows

Start with [AGENTS.md](AGENTS.md). It contains the default command and rules
for ordinary calculations. This page covers other workflows;
[task recipes](docs/AGENT-RECIPES.md) supply calculation syntax and
[API.md](API.md) is the detailed CLI/HTTP reference. Use the executable beside
these documents, without changing your task directory.

## Batch, adapt, or run a notebook

Use one `eval --file problem.wl --session task_001 --brief --output results.json`
for a known batch. Add `--open-ui` to the final command for desktop delivery.
`--brief` puts answers on stdout even with `--output`; read the JSON only if you
need omitted LaTeX, plot arrays or execution metadata. A calculation is limited
to 24,000 characters and 40 visible results. For larger work use multiple cells.

For adaptive work, keep `calix-cli.exe pipe --brief --output transcript.json`
running. Write and flush a JSONL request, read its response, then choose the next:

```jsonl
{"id":"define","code":"a=41;"}
{"id":"answer","code":"a+1"}
```

All requests share a session. `id` is echoed; no startup banner is printed.
`--timeout` applies to each request. Close stdin to save the full transcript.
Add `--notebook answer.cixnb --open-ui` at launch for desktop delivery at EOF.
Invalid lines and calculation errors do not stop later requests; inspect each
response. If your tool cannot keep stdin open, batch with `eval --file` instead.

Use `run input.cixnb --brief --output results.json --notebook answer.cixnb`
for existing notebooks. It preserves text cells, runs calculations in order in a
fresh session and stops at the first calculation error. Add `--session` only when
deliberately reusing state. Input files are not overwritten.

## Create a notebook with text and contents

`eval --file ... --notebook answer.cixnb` exports one calculation cell. Each
visible line is an output, **not a separate cell**. `pipe --notebook` exports one
calculation cell per request. Neither inserts Markdown descriptions.

For mixed text/calculation cells, write minimal **input-only** JSON with a real
JSON serializer, UTF-8 (optional BOM), and a `.cixnb` extension:

```json
{"format":"calix-notebook","version":1,"title":"Root calculation","cells":[{"mode":"markdown","code":"# Root calculation\n\n## Bisection bracket\nFind the positive root."},{"mode":"source","code":"FindRoot[x^2-2,{x,0,2}]"}]}
```

Use `run input.cixnb --notebook answer.cixnb --brief --open-ui`, then
`validate answer.cixnb`. Let Calix serialize results; do not fabricate result
objects, `latex`, counters or a `toc` field. Markdown headings `#` through
`######` automatically create GUI contents. No contents metadata is required.

Limits: 1-200 cells, 24,000 characters per cell, 10 MB per notebook. `validate`
checks structure/syntax without starting the service; it does not verify answers.
Keep input, result notebook and JSON report at different paths.

## Interpret completion and recover

Exit codes: 0 success, 1 calculation error, 2 input/client/API/UI failure,
130 interruption. Check `ok` and the expression, not just the code.
`unresolved:true` means incomplete evaluation; remaining symbolic variables can
be intentional. Brief results retain `unresolved`; full results also contain
`evaluation_status`, `variables` and `symbolic_functions` when available.

Results are `expression`, nested `group.items`, `plot`, or `animation`.
Plot/animation arrays are in full JSON. `run` returns a `cells` array of evaluated
calculation cells only. A pipe's final `event:"ui"` or `event:"notebook"` record
describes delivery, not another calculation result.

An ordinary engine error may leave earlier assignments. Use a new session or
`reset NAME` before an independent retry. Timeout/cancel clears state: restore
definitions before continuing. Use `cancel NAME` from another client or Ctrl+C.
Do not retry unsupported expressions unchanged. See the
[recovery table](docs/AGENT-RECIPES.md#recovery).

## Desktop delivery and versions

Use `--open-ui` only at completion. Check `ui.opened` and `ui.notebook`.
Without `--notebook`, Calix creates a unique `calix-handoff-*.cixnb` beside
`--output` or in the local handoff directory. UI failure preserves results but
returns code 2. Retry `open-ui --notebook PATH` rather than recalculating.
The GUI uses a fresh kernel; saved outputs appear stale until rerun.

If double-click starts an older installation, use the intended installation's
`calix-cli.exe open-ui --notebook PATH`. `CALIX_UI_PATH` selects a desktop
executable explicitly. Source, installed app and previews can differ; updating
GitHub source does not update installed binaries.

## Read only when needed

- Syntax/compatibility: [supported syntax](docs/SUPPORTED-SYNTAX.md).
- FEM/flow: [PDE scope](docs/PDE.md) and the closest shipped example. Familiar
  Wolfram names do not imply general Mathematica FEM support.
- Performance: [CPU execution](docs/CPU-ACCELERATION.md). Workers is a limit,
  not measured utilization; increasing it does not speed every calculation.
- HTTP integration: [API reference](API.md). Prefer CLI connection discovery;
  never print or share tokens.
