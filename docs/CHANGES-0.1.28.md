# Calix 0.1.28

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

## Maintenance

The source has a local Git baseline. Windows verification workflows and bounded
core/numerical/example test tiers retain machine-readable results. Native setup
can download versioned Boost and checksum-verified Eigen archives. Standard Rust
installations are supported by desktop packaging scripts. Build records carry
the source commit, dirty status, source digest and dependency-lock hashes.

The application license and repository URL remain undecided. Windows signing,
clean-machine installation qualification and AVX-512/AMX execution on matching
hardware remain separate release requirements.
