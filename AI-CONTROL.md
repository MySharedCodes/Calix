# Calix AI Control

Calix is installed at `D:\Calix\App` on this machine. It is a local symbolic
and numerical calculator. The supported input is a documented Wolfram-language
subset; it is not Python. `AGENTS.md` is sufficient for routine tasks; use this
guide or `API.md` only when needed.

## One File, One Call

Put related expressions in one UTF-8 `.wl` file, one expression per line.
Use `;` after definitions that should not produce output. Make one call:

```powershell
& 'D:\Calix\App\calix-cli.exe' eval --file problem.wl --output results.json --brief --open-ui
```

No preliminary `start`, `status` or schema request is required. `--brief` returns
answers directly on stdout, including when `--output` is used, avoiding a second
file-read operation. Full LaTeX, plots, animations and timing remain in the JSON
file. Brief plot/animation results are summaries. Use `run` when separate cells
are required. The native CLI loads a lightweight client without the web framework.

## Interactive Calls

For a notebook deliverable, add `--notebook answer.cixnb --title "Problem title"`
to `eval` or `run`. Calix serializes the evaluated input and output as UTF-8
without a BOM. Prefer this to manually writing notebook JSON. Then run
`calix-cli.exe validate answer.cixnb` for structure and syntax checks. Validation
is local and does not start the calculation service or verify numerical answers.
User-authored files with a leading UTF-8 BOM are also accepted by the GUI and CLI.

For adaptive calculations, start `calix-cli.exe pipe --brief` once. Send UTF-8
JSON lines such as `{"id":"q1","code":"a=41"}` and
`{"id":"q2","code":"a+1"}` through stdin, and read one flushed JSON response
per line. The process retains its connection and session. Invalid lines return
errors and allow the next request. Use `--output results.json` to save full
responses at EOF. Add `--open-ui` to open the input/output transcript when stdin
closes (up to 200 cells / 10 MB). The `id` is echoed for correlation.
Use `cancel SESSION` from another client to interrupt an active calculation;
cancellation clears that session. Ctrl+C also requests cancellation.

## Other Entry Points

Use the native launcher so Windows does not alter `^`, `&`, `>` or quotes:

```powershell
& 'D:\Calix\App\calix-cli.exe' status
& 'D:\Calix\App\calix-cli.exe' start --workers 8
& 'D:\Calix\App\calix-cli.exe' eval --session task1 --code 'Solve[x^2==2,x]'
& 'D:\Calix\App\calix-cli.exe' eval --session task1 --file 'problem.wl' --output 'answer.json'
& 'D:\Calix\App\calix-cli.exe' run 'problem.cixnb' --output 'notebook-results.json'
```

Use `eval --file` for multiline input. A file is UTF-8 and is limited to 10 MB;
one calculation cell is limited to 24,000 characters. A semicolon suppresses an
intermediate result. Use the same `--session` for definitions that must persist.
Each response is JSON. Check both the process exit code and the JSON `ok` field.
An engine error has `ok:false`; do not silently replace it with a guessed result.

## Finish by opening the user interface

After an AI-controlled run, open the desktop with:

```powershell
& 'D:\Calix\App\calix-cli.exe' run 'problem.cixnb' --output 'results.json' --open-ui
```

Use `--open-ui` on the final `eval` or `run`, not on every intermediate command.
It writes a uniquely named `calix-handoff-*.cixnb` beside the JSON report (or in
the user-local Calix handoffs directory), then opens it with saved outputs.
The source notebook is not overwritten. Check `ui.opened` and `ui.notebook`.
The desktop uses a fresh kernel; saved outputs are marked stale, and definitions
must be rerun before continuing. A failed cell is preserved and later cells
remain unevaluated. A desktop launch failure returns exit code 2 but preserves
the calculation response. For an existing notebook use
`open-ui --notebook problem.cixnb`; plain `open-ui` opens the workspace.
`open-ui` does not require a running calculation service. `eval` and `run`
start a headless service when needed. `CALIX_UI_PATH` overrides the desktop path.

Batch independent expressions in one UTF-8 `.wl` file (one expression per line)
or use a notebook. This avoids starting a client process for each expression.
For notebooks, use this minimal file structure:

```json
{"format":"calix-notebook","version":1,"title":"Calculation","cells":[{"mode":"source","code":"Sum[k^6,{k,1,500}]"},{"mode":"source","code":"Plot[Sin[x],{x,0,6}]"}]}
```

## Common expressions

```wolfram
Sum[k^4,{k,1,100}]
Integrate[Exp[-x^2],{x,-Infinity,Infinity}]
Solve[{x+y==3,x*y==2},{x,y}]
Factor[x^6-1]
D[x^3*y^2,x]
DSolve[{x''[t]+2*x'[t]+5*x[t]==0,x[0]==1,x'[0]==0},x[t],t]
UnitConvert[650[gr],"g"]
Plot[Exp[-t] Cos[2 t],{t,0,10}]
```

`gr` means grain. Units can be entered directly, including compound units such
as `890[m/s]`; outputs carry visible units. Results can be `expression`, `group`,
`plot` or `animation`. Plot results contain numerical data and options, not a
PNG screenshot.

## HTTP API

The CLI is preferred because it discovers the private loopback connection file.
For direct HTTP control, read `%LOCALAPPDATA%\com.calix.desktop\api\connection-*.json`,
verify the URL is `http://127.0.0.1:<port>`, and send `X-Calix-Token`. Use
`GET /api/health`, `GET /api/capabilities`, `POST /api/evaluate`,
`POST /api/cancel/{session}`, `POST /api/settings`, and `POST /api/open-ui`.
Never print or include the token in a prompt, report, or shared file.

## Limits and recovery

The default Workers limit is the physical-core count; `--workers 8` is useful for
debugging on this machine. AVX2 is enabled here; AVX-512 and AMX are compiled as
optional paths but are selected only when hardware and OS support them. After a
timeout or cancellation, the target session is cleared. Start a new session or
re-run definitions deliberately. Do not claim a calculation succeeded because a
button was clicked; use the JSON response as the evidence.
