# Contributing to Calix / 参与 Calix

Calix welcomes reproducible bug reports, verified examples, documentation corrections
and translation feedback. Calix-owned code, documentation and examples use
[GPL-3.0-only](LICENSE). Contributions to those files are submitted under the same
license; contributors retain copyright. Submit only work you can license on those
terms and identify any third-party material and its license. No separate CLA or
copyright transfer is required by this document.

The source repository is [MySharedCodes/Calix](https://github.com/MySharedCodes/Calix).
Use [Issues](https://github.com/MySharedCodes/Calix/issues) for reports and proposals,
and pull requests for code or documentation changes. See
[licensing and publication status](docs/LICENSING.md).

## Report a Calculation Error

Reduce the problem to the smallest expression that fails in a fresh session.
Include the exact input as text, actual result or complete error, expected result
and how you checked it. A screenshot helps with formula layout, but cannot replace
copyable input. If it involves earlier definitions, include them in order.

```text
Calix version:
Windows version / CPU:
Installed components:
Workers / numerical precision:
Steps: Run All or individual cell; fresh or existing session?
Input:
Actual result:
Expected result and independent check:
```

Use the issue templates in the [public repository](https://github.com/MySharedCodes/Calix/issues/new/choose).
Remove API tokens, private notebooks, local account names and personal data.
Security issues follow [SECURITY.md](SECURITY.md).

## Improve Documentation and Examples

Documentation lives in `docs/`; [the index](docs/README.md) is the starting point.
Keep the English and Chinese README overviews consistent. A function should have
a runnable example and its important limits. Describe only verified behavior;
do not label a partial Wolfram implementation as Mathematica compatible.

Use short, descriptive titles and direct problem statements. Put calculation into
calculation cells and explanation into text cells. Use one-character mathematical
symbols or indexed symbols in notebooks. Include units where they are part of
the physical model, and state assumptions and a way to check the answer.
Do not copy third-party problem statements, images or solution text without
checking the relevant rights and attribution requirements.

## Propose a Change

Explain the user-visible problem, the resulting behavior, and the validation
performed. Keep changes focused. For a mathematical correction, use an independent
identity, substitution, conservation law or reference value as evidence.
Do not add snapshots that merely repeat the implementation's own answer.

See [development](docs/DEVELOPMENT.md) for setup. Typical checks are:

```powershell
npm.cmd run build
.\.venv\Scripts\python.exe -m pytest tests/test_engine.py -q -k "not shipped_examples and not physics_starter"
.\.venv\Scripts\python.exe scripts/check-docs.py
```

Select additional tests for the affected component. Changes to optional PDE code
need the corresponding dependencies and native runtime. Document any checks you
could not perform. Do not commit build outputs, credentials, personal notebooks
or files from `work/`, `App/`, `tools/` and `release/`.

## Translations

Core UI strings are in `frontend/src/i18n.ts`; the optional language catalog is in
`frontend/src/locales.ts`. Preserve interpolation tokens, mathematical notation
and function names. Check long labels in the actual UI and report which language
you tested. Technical documents currently focus on Chinese, with an English
README and CLI/API reference; the additional UI languages do not imply translated
manuals.
