# Calix: calculate first

Calix accepts a **Wolfram-language subset**, not Python or full Mathematica.
Use `calix-cli.exe` beside this file; pass its absolute path when working elsewhere.
On this workstation the installed copy is `D:/Calix/App/calix-cli.exe`.
Save task files in your task directory, not the installation or source tree.

## Default: one file, one call

Write related expressions to a UTF-8 `problem.wl`, one result per line. End
intermediate definitions with `;`. Choose a new session name per independent task:

```powershell
& 'D:\Calix\App\calix-cli.exe' eval --file problem.wl --session task_001 --brief --output results.json --open-ui
```

The service starts automatically. No `start`, `status`, `schema`, source-code
inspection or dependency installation is needed for a normal calculation.
Stdout contains answers; the file retains full results and plot data.
Open the UI on the final call only; omit `--open-ui` for headless tasks.

| Need | Use |
| --- | --- |
| Expressions known in advance | One `eval --file` (up to 40 visible results) |
| Next step depends on a result | One `pipe --brief`; JSONL `{"id":1,"code":"1+1"}` |
| Existing notebook with text cells | `run input.cixnb --brief --notebook answer.cixnb --open-ui` |
| Export calculated inputs/outputs | Add `--notebook answer.cixnb --title "Title"` |
| Open saved results without recalculating | `open-ui --notebook answer.cixnb` |

## Avoid retries

- Calls use `Sin[x]`, lists `{x,y}`, powers `x^2`, equations `==`, assignment `=`.
  Use `Pi`, `I`, `Infinity`; use `Dot[a,b]` for matrix multiplication.
- No `f[x_]:=...`, patterns or packages. Use `f=x^2; ReplaceAll[f,x->3]`.
  `FindRoot[f,{x,a,b}]` needs a real sign-changing **bracket**, not one guess.
- Keep exact inputs as fractions; use `N[expr,30]` when decimals are needed.
  Units: `890[m/s]`; `gr` is grain, `g` is gram.
- Check exit code AND `ok`. `unresolved:true` means evaluation is incomplete;
  a symbolic result with remaining variables is not automatically an error.
  See [tested recipes](docs/AGENT-RECIPES.md) for task syntax and recovery.
- Reuse `--session` only for dependent calls. Timeout/cancel clears its state.
  GUI handoff opens saved outputs in a fresh kernel; rerun definitions to continue.

Prefer official notebook export. For text/heading cells, see the short authoring
recipe in [AI-CONTROL.md](AI-CONTROL.md). `validate answer.cixnb` checks structure
and syntax, not answers. Do not overwrite user inputs or edit application source
to solve a calculation. Never print/share the local API token.
Read [API.md](API.md) only for HTTP integration or detailed command semantics.
