# Calix 0.1.27

## Documentation and Offline Help

The English and Chinese README pages now lead to installation, quick start,
usage, troubleshooting and a linked example catalog. Development, contribution,
security and release-preparation guides describe the current project status.
The public repository and open-source license remain undecided; the existing
application license has not changed.

The sidebar Help button and F1 open searchable offline documentation, with local
article navigation and notebook links. Opening help does not execute examples.
Documentation and actual UI screenshots are included in the distribution.
The syntax reference now reflects inline formulas, the 180-second default
deadline, 128 stored sessions and the supported parallel sparse solver.

## Calculation and CLI Updates

Expression output combines square-root factors with provably positive real
radicands, for example sqrt(3)*sqrt(pi)/36 becomes sqrt(3*pi)/36. This applies
to LaTeX and reusable expression text, including nested outputs and units.
Unknown signs and complex branches are preserved. Kernel values are unchanged;
formatting does not run a global symbolic simplifier.

The packaged CLI no longer imports the web framework at startup. `eval` and
`run` accept `--brief`, which prints compact answers even when saving a full
JSON response with `--output`. The complete response remains in the file.
Plots and animations become summaries only in brief stdout.

`pipe` accepts JSONL requests and emits flushed JSONL responses while retaining
the client connection and calculation session. It supports saved transcripts
and opens an input/output notebook at EOF with `--open-ui`. Engine or malformed
request errors allow subsequent lines; failed requests produce a nonzero exit.

AGENTS.md gives a self-contained first call using one multi-expression `.wl`
file. Additional API documentation is optional for routine tasks, eliminating
mandatory reference reading and preliminary status/schema calls.

Connection discovery skips records belonging to exited processes before HTTP
probing. Active processes still require the authenticated application/PID check.
This removes accumulated two-second waits after interrupted desktop sessions.

Windows file associations can pass the notebook as a positional argument.
Calix now opens and activates that file, preserving `--notebook PATH` support.
All notebook text entry points accept a leading UTF-8 BOM. Characters within
the notebook body are preserved.

`--notebook answer.cixnb` exports evaluated notebooks through the official
serializer; `--title` sets their title. `validate` checks notebook structure
and code syntax without starting a service. This avoids hand-written JSON and
encoding inconsistencies when another AI produces a notebook deliverable.

The calculator keypad replaces fixed unit and punctuation shortcuts with
determinants, matrix inverses/transposes/eigenvalues, statistics, rational and
complex simplification, analytical/numerical extrema and animation. All pages
retain a run button with a play icon. New commands insert editable inputs into
the same calculation editor; labels fit the fixed buttons in all seven locales.
