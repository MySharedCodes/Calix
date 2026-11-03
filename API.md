# Calix Command Line and Local API

Calix is a local calculator for a supported subset of Wolfram-language syntax.
The command line and notebook share a computation service. Exact arithmetic,
symbolic algebra, calculus, equations, units, statistics, plots and numerical
solvers are available. PDE calculations require the optional PDE module.
This is not a complete implementation of the Wolfram Language.

## Command Line

Run commands from the installation directory in PowerShell. The launcher also
accepts an absolute path from another directory; input and output paths remain
relative to the caller's current directory:

```powershell
.\calix-cli.exe --help
.\calix-cli.exe status
.\calix-cli.exe start --workers 8
.\calix-cli.exe eval --code 'Sum[k^4,{k,1,100}]'
.\calix-cli.exe eval --session example --code 'a=41'
.\calix-cli.exe eval --session example --code 'a+1'
.\calix-cli.exe sessions
.\calix-cli.exe reset example
.\calix-cli.exe open-ui
```

The client discovers a running Calix service. If none is running, `start`,
`eval` and `run` start a headless service. Other commands return a clear error
when no service is available. `start --workers N` and `workers N` set the CPU
limit for the connected service, including desktop calculations if connected
to the desktop service. The limit cannot exceed the physical core count.

The default evaluation session is `cli`. Its definitions persist between
commands until cancellation, reset or service exit. Desktop notebooks use
different session IDs. Use a unique session name for independent calculations.
Cancellation clears all definitions in the target session.

Source files avoid shell quoting problems. Files use UTF-8:

```powershell
.\calix-cli.exe eval --file work\problem.wl --session problem --timeout 300 --output work\answer.json
.\calix-cli.exe run work\problem.cixnb --timeout 300 --output work\notebook-results.json
.\calix-cli.exe cancel problem
.\calix-cli.exe schema
.\calix-cli.exe stop
```

`eval` accepts exactly one of `--code`, `--file`, or `--stdin`. `run` evaluates
calculation cells in order in a fresh session, skips text cells, and stops at
the first calculation error. Supply `--session` to reuse definitions deliberately.
Input notebooks are never modified. Outputs from `run` are a JSON report, not
a replacement notebook. `stop` only shuts down a CLI-owned service; close the
desktop window to stop a desktop-owned service.

For the lowest task overhead, submit a single `.wl` file containing multiple
newline-separated expressions. No preliminary `start` or `status` is needed.
Add `--brief` to `eval` or `run` for compact answers on stdout. When combined
with `--output`, stdout also includes these answers; the file retains complete
results, LaTeX, plots and execution metadata. Brief plot/animation results are
summaries; read the full file when numerical plot data are required.

`eval`, `run` and `pipe` accept `--notebook answer.cixnb` to export evaluated
inputs and outputs with Calix's own UTF-8 serializer. `--title NAME` sets the
title. With `--open-ui`, the exported file is opened directly. Without it,
the file is saved without opening a window. Input/output path collisions are
rejected. Use this export instead of generating notebook JSON by hand.

`calix-cli.exe validate answer.cixnb` works without a running service. It accepts
UTF-8 with an optional leading BOM, checks notebook structure, cell limits and
calculation syntax, and returns JSON. It does not evaluate expressions or assert
the mathematical correctness of saved results. Both Windows double-click and
`open-ui --notebook PATH` activate the specified document.

### Persistent JSONL Client

`calix-cli.exe pipe --brief --output transcript.json --open-ui` reads one JSON
request per line and flushes one JSON response per line. Requests have a required
`code` string and optional `id` (string/integer, at most 200 characters). Responses
echo `id`. All expressions share one session, named with `--session NAME` or
generated automatically. `--timeout` applies to each evaluation. Invalid requests
or engine errors do not stop subsequent lines; EOF returns exit code 1 if any
request failed. Transport/startup errors can return code 2. No banner is printed.

```jsonl
{"id":"definition","code":"a=41"}
{"id":"answer","code":"a+1"}
```

Keep stdin open for adaptive calculations, writing and flushing the next line
after inspecting the previous response. This amortizes client startup and
connection discovery. Closing stdin writes the full transcript when `--output`
is set; `--open-ui` opens a result notebook and emits a final
`{"event":"ui","ok":true,"ui":{...}}` line. Handoffs support 1 to 200 cells
and 10 MB. Use another client to cancel the active session. Full transcripts
retain failed calculations. A pipe's session remains available after EOF.

The native launcher forwards arguments without a command shell, preserving
expression characters such as `^`, `&`, and `>`. The legacy `calix.cmd` wrapper
supports files and stdin, but rejects `--code` because Windows batch processing
can change the expression before the calculator receives it.

Append `--open-ui` to `eval` or `run` to launch the desktop after that command
finishes. `open-ui` can also be run by itself and returns the executable path and
process ID. The same operation is available to authenticated HTTP clients as
`POST /api/open-ui`.

`--open-ui` also saves the evaluated inputs and results in a unique
`calix-handoff-*.cixnb`, beside `--output` or in the user-local handoffs folder.
The returned `ui.notebook` names it. The desktop opens that notebook with saved
outputs; rerun definitions to continue in its fresh kernel. The input notebook
is never overwritten. Launch failure preserves results and returns exit code 2.
`open-ui --notebook PATH` opens an existing notebook; HTTP clients can pass
`{"notebook":"D:/path/problem.cixnb"}` to `/api/open-ui`.

Without `--output`, stdout contains one JSON object. With `--output`, the full
response is saved atomically and stdout contains its path and success status.
Exit codes are 0 for success, 1 for a calculation error, 2 for client/API/input
errors, and 130 for keyboard interruption. Ctrl+C during evaluation requests
cancellation. The HTTP timeout is the requested computation timeout plus a
small connection allowance.

An `eval` response has this structure:

```json
{"ok":true,"session":"cli","request_id":"...","result":{"kind":"expression","text":"42","latex":"42","elapsed_ms":1.2,"engine":"SymPy","execution":{}}}
```

An engine error has `ok:false`, `error`, and `error_type`. Always check both
the exit code and `ok`. Definitions made before an engine error may persist;
use `reset` for a clean session. A timeout or cancellation clears the session.

## Calculation Input

Function names are case-sensitive. Square brackets call functions; braces
create lists. A newline produces a visible result. A semicolon suppresses
intermediate output. Variables can be assigned with `=`. Equality is `==`.
Use `Clear[x,y]` to remove definitions.

```wolfram
Sum[k^4,{k,1,100}]
Integrate[Exp[-x^2],{x,-Infinity,Infinity}]
Factor[x^6-1]
Series[Sin[x]/x,{x,0,8}]
Solve[{x+y==3,x*y==2},{x,y}]
D[x^3*y^2,x]
DSolve[{x''[t]+2*x'[t]+5*x[t]==0,x[0]==1,x'[0]==0},x[t],t]
Det[{{2,1,0},{1,3,1},{0,1,2}}]
UnitConvert[650[gr],"g"]
UnitConvert[3[m]+20[cm],"cm"]
Fit[{{0,1},{1,3},{2,5}},{1,x},x]
Plot[Exp[-t]*(Cos[2*t]+Sin[2*t]/2),{t,0,10}]
```

Units are entered directly as suffixes such as `650[gr]`, `890[m/s]` and
`7[km]`. `gr` means grain, not gram (`g`). Exact calculations remain exact
unless `N[expression,digits]` or a numerical solver is used. Symbols which
remain in an output may represent a valid symbolic result or an unsupported
function; do not describe such an output as a completed numerical evaluation.

Results have kinds `expression`, `plot`, `animation` or `group`. Expression
results include plain text and LaTeX. Plots include numerical data and display
options rather than a screenshot. Groups contain an `items` array. The
`execution` metadata reports the CPU thread limit and native operations where
applicable; an assigned limit is not a measurement of CPU utilization.

Notebook input is JSON with this structure:

```json
{"format":"calix-notebook","version":1,"title":"Example","cells":[{"id":"description","mode":"markdown","code":"# Problem"},{"id":"input","mode":"source","code":"a=6;\na^2"}]}
```

## HTTP API

The service binds only to `127.0.0.1` on a dynamically allocated port.
Per-user connection records are under
`%LOCALAPPDATA%\com.calix.desktop\api\connection-*.json`. These private files
contain the loopback URL, role, PID and authentication token. They are removed
on normal service exit; clients validate the service PID and authentication
before using a record. Prefer the CLI so callers need not handle tokens.

Every endpoint except `GET /api/health` requires `X-Calix-Token`. The full
authenticated OpenAPI schema is at `GET /api/openapi.json`.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Version, CPU features, Worker limit and components |
| `GET /api/capabilities` | API version, service identity, input/result limits |
| `GET /api/openapi.json` | Machine-readable request schema |
| `GET /api/sessions` | Session IDs, busy state and current request IDs |
| `POST /api/evaluate` | Evaluate one calculation cell |
| `POST /api/cancel/{session}` | Stop the calculation and clear the session |
| `POST /api/settings` | Set `max_workers` |
| `POST /api/shutdown` | Gracefully stop a CLI-owned service |

`POST /api/evaluate` accepts `session`, `code`, an optional `request_id`, and
optional `timeout_seconds` (default 180, range 0.01 to 3600). Its response
echoes session and request IDs. Session/request IDs use letters, numbers,
underscores and hyphens, at most 80 characters. One cell contains at most
24,000 characters; at most 128 sessions are retained. The same session rejects
concurrent evaluations with HTTP 409. Independent sessions can run concurrently
within the configured Worker budget. Idle sessions can be reclaimed after
five minutes when the session limit is reached.

Invalid input returns HTTP 422, missing/invalid credentials 403, timeout 408,
busy/cancelled session 409 and session exhaustion 429. Calculation errors use
HTTP 200 with `ok:false`; this distinguishes a failed mathematical operation
from a failed API request. Do not automatically resubmit a timed-out or
cancelled calculation with old assumptions about its variable state.
