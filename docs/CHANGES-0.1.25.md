# Calix 0.1.25

## Gear stress postprocessing

Machine-precision triangle Jacobians, gradients and coordinate means now use
numeric matrix operations instead of repeatedly constructing symbolic matrices.
Exact rational arithmetic and arbitrary-precision inputs retain their symbolic
paths. The solved displacement field is not modified by postprocessing.

On the same saved solution (13,780 nodes, 23,077 triangles, 8 Workers), the last
gear calculation cell decreased from 144.26 s to 37.06 s, a 3.89x speedup.
All five outputs were compared: stress peaks, scalar legend ranges, triangle
coordinates and vertex colors agree with the baseline. These timings measure
postprocessing, not the finite-element solve or browser rendering.

## Calculator derivative input

The derivative button inserts an editable partial derivative with a subscript,
using the same inline formula editor as notebook cells. Esc-pdiff-Esc inserts
the same template. Ctrl+Enter evaluates it; second derivatives are supported.

## Command line and local API

The installed runtime includes calix-cli.exe, API.md and AGENTS.md. An external
command-line agent can read the directory documentation and use the calculator
without receiving product instructions in its task prompt.

The CLI discovers authenticated local services, can start a headless service,
keeps named sessions, reads UTF-8 expression files, runs notebook cells in
order, cancels calculations, controls Worker limits and saves JSON responses.
Relative file paths are resolved from the caller's current directory.
The native command-line launcher preserves expression characters such as ^
without passing through a batch shell. The legacy calix.cmd accepts file and
stdin input but rejects inline --code, preventing silent shell transformations.
The API adds authenticated capabilities, session inspection, OpenAPI and
headless-service shutdown endpoints, request IDs, per-request timeouts and an
open-ui endpoint for handing control back to the user after an AI run.

Six calculations were executed by DeepSeek Harness through the CLI: a finite
sum, Gaussian integral, algebraic system, determinant and inverse, ODE and
solution samples, and kinetic energy with units. Raw input/output files and
the agent's report are retained under work/deepseek-v0125.

## Validation and limits

The complete Python regression run passed 284 tests; the subsequent CLI suite
passed all 7 tests, including relative paths and native argument forwarding.
Real keyboard UI tests covered first and second partial derivatives and the
shared notebook shortcut.

Calix implements a subset of Wolfram-language syntax. For example, Table does
not currently substitute iterator values recursively into a previously stored
symbolic expression. Evaluate the explicit returned expression in Table or
sample it with Plot. The DeepSeek report records the workaround used.
