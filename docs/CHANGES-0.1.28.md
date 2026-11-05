# Calix 0.1.28

## Text Editing and Contents

Text cells now support font sizes, emphasis, headings 1–6, lists and editable
mathematics, alongside Markdown source editing. Formatting remains in the notebook
file, and rendered HTML is sanitized.

Headings automatically enable a searchable contents panel. Entries navigate to
individual headings, including repeated titles, and update when cells change.
The panel reserves document space, adapts to narrow windows and respects reduced
motion preferences. A toolbar command clears all outputs while retaining input
cells and session variables.

## Notebook Recovery

Desktop workspaces now have a separate disk recovery copy, written through a
flushed temporary file before replacement. Up to 20 previous workspace revisions
are retained, normally at one-minute intervals and at structural checkpoints.
Falling back to disk no longer depends on an intact WebView local-storage copy.
Recovery history opens a selected notebook as a new document; the original is kept.

Saving over a notebook preserves its previous content in the adjacent
`.calix-history/<filename>/` directory. Saved-file versions are available in the
recovery window when that notebook is active. Backups are local and unencrypted.
They do not replace an external backup or guarantee survival of disk failure.

Cell insertion, deletion, duplication and movement support 20 levels of structural
undo/redo. Restored results are stale; kernel definitions are not rolled back.
Text editing retains its own editor undo history.

## Calculation Reliability

Numerical ODE interpolants now accept direct calls such as `u[0.5]`; these were
previously misclassified as unit suffixes. Independent checks cover rational
arithmetic, polynomial derivatives, quadrature, root residuals, oscillator energy,
statistics, affine units and complex branches. Output metadata distinguishes
unevaluated operations and symbolic functions from evaluated expressions.

Finite indexed sums and products now evaluate scalar data through bounded
iteration. Mixed list/matrix addition and subtraction use consistent array
semantics. `TableForm` and `MatrixForm` support rectangular scalar data; see
[supported syntax](SUPPORTED-SYNTAX.md) for their current limits.

## Maintenance

The source has a local Git baseline. Windows verification workflows and bounded
core/numerical/example test tiers retain machine-readable results. Native setup
can download versioned Boost and checksum-verified Eigen archives. Standard Rust
installations are supported by desktop packaging scripts. Build records carry
the source commit, dirty status, source digest and dependency-lock hashes.

Calix-owned source is licensed under GPL-3.0-only and published at
[MySharedCodes/Calix](https://github.com/MySharedCodes/Calix). Windows signing,
clean-machine installation qualification and AVX-512/AMX execution on matching
hardware remain separate release requirements.
