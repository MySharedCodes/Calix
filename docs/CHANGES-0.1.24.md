# Calix 0.1.24

Formula templates now insert immediately into the calculation cell at its
current cursor position. The notebook and traditional calculator use the same
editable inline math fields. Integral, sum, product, root and keyboard templates
no longer open a separate formula composer or require an Insert confirmation.
The special-character search palette remains a floating picker below the caret.

Inline editing updates executable source and preserves the math caret as source
length changes. Tab moves between placeholders; Ctrl+Enter evaluates the cell.
Unfinished templates remain in the cell, survive notebook autosave/reload and
are blocked from evaluation with an incomplete-input message. Older saved
formula decorations open as editable fields. History recall and source
undo/redo retain formula presentation.

The traditional calculator remains one cell without notebook saving controls.
Calculation engines, PDE examples and sparse solver binaries are unchanged.
