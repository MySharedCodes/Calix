# Calix 0.1.10

- The English default document name is Untitled CIX notebook. The workspace view is named CIX Notebook.
- Example source uses Labeled[expression,"description"] to identify displayed quantities, checks, solutions and plots. Values assigned before labeling remain available for subsequent calculations.
- The hydrogen-like ion notebook retains its analytic eigenstate, energy, equation and normalization calculations. Its probability section now contains only six volume-rendered probability clouds: 1s, 2s, 2p_z, 3s, 3p_z and 3d_z2, with m=0 and Z=2.
- Each cloud identifies its coordinate bounds in Bohr radii. Density maxima are in a0^-3. Opacity is proportional to (density / sampled maximum)^0.45, independently normalized per state, and has an adjustable multiplier. Cloud color does not encode wavefunction phase. Volumes use a 49^3 lattice and square-root byte encoding to preserve low-density tails in notebook autosaves.
- The current-loop scene combines the coil, current direction, magnetic-field arrows, proton trajectory and starting point. Field arrows have equal length and encode direction only. Coordinates are normalized by coil radius. The magnetic-field values come from the notebook's elliptic-integral expressions; the trajectory is integrated numerically.
- DensityPlot3D samples nonnegative scalar fields through the native C++ batch evaluator when supported. Graphics3D supports Line, Point, Arrow, Style and bounded primitive Table expressions. Both are interactive, export to PNG and survive save/reopen.
- Compound expressions separated by semicolons are supported inside function arguments, lists and parentheses, allowing intermediate calculations within Table.
- Reapplying the active CPU Workers limit is a no-op, so a second preview window can connect while calculations run. Changing the limit still requires idle workers.

No dependencies were added. Closed-source distribution continues to include the existing third-party notices.

Regenerate examples with create-case-notebooks.py, create-examples.py, annotate-examples.py, then export-library.cjs. Existing saved user documents are preserved; revised built-in notebooks have a new example version key.
