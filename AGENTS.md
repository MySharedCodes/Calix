# Calix: Fast Calculation Entry

Use `D:/Calix/App/calix-cli.exe` (or `./calix-cli.exe` in this directory).
Input is a supported Wolfram-language subset, not Python. For routine tasks,
this file is enough; consult AI-CONTROL.md or API.md only when needed.

Write ALL related expressions to one UTF-8 `problem.wl`, one result per line.
Use `;` to suppress intermediate definitions. Then make ONE call:

```powershell
& 'D:\Calix\App\calix-cli.exe' eval --file problem.wl --output results.json --brief --open-ui
```

The command starts the service if needed. Stdout contains compact actual answers;
the JSON file retains full results. Check exit code and `ok`. Omit `--open-ui`
when the task requests headless timing. No preliminary status/start/schema call
is needed. Do not create a notebook unless the task needs separate cells.

To deliver a notebook, add `--notebook answer.cixnb --title "Problem title"`.
Calix writes valid UTF-8 and includes actual outputs. Avoid hand-authoring notebook
JSON. Check it with `calix-cli.exe validate answer.cixnb` before delivery; this
checks structure and calculation syntax without executing. A valid notebook may
still require calculations to be rerun; use the official export to retain results.

Syntax: `Sum[k^6,{k,1,500}]`, `Integrate[x^4 Exp[-3 x^2],{x,-Infinity,Infinity}]`,
`Solve[{x+y==3,x*y==2},{x,y}]`, `Det[m]`, `Inverse[m]`,
`DSolve[{x''[t]+3 x'[t]+2 x[t]==Exp[-t],x[0]==0,x'[0]==1},x[t],t]`,
`UnitConvert[650[gr],"g"]`. `gr` is grain. Units use `890[m/s]`.
For equation systems use `Solve[equations, variables]`; explicit domain arguments
on systems are currently unsupported. Check that returned solutions meet the
problem's real/integer constraints.

Use the same `--session NAME` for dependent calls. For interactive sequences,
`pipe --brief` accepts JSONL `{"id":1,"code":"1+1"}` and flushes one response
per line without restarting the client. Add `--open-ui` to open results at EOF.
Desktop handoff shows saved outputs in a fresh kernel; rerun definitions to continue.
Save artifacts in the task directory. Do not edit application source or user
notebooks for calculations. Report unsupported expressions and errors explicitly.
Never print or share the private local API token.
