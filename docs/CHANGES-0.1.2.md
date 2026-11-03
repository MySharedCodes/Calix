# Calix 0.1.2

- Notebook toolbar stays at the top while scrolling. Text cells appear immediately after math cells. Code and math retain their distinct Wolfram/2D formula input methods and share the same evaluator.
- Added explicit Save As actions beside Save in the document header and in the sidebar. Ctrl+Shift+S also opens Save As. The selected copy becomes the active file for subsequent saves.
- Sidebar File actions now precede Workspace navigation.
- The projectile notebook has ten alternating text/computation cells. DSolveValue returns the velocity vector directly; In[2] integrates both components in one line. The two time plots share a single code cell, as do the final consistency checks.
- The last projectile plot is a trajectory animation: a moving point and progressively drawn path. Controls include play/pause, reset, seeking, speed and loop. Animation starts paused; PNG export captures the current frame.
- `Animate[ParametricPlot[{Cos[t],Sin[t]},{t,0,2 Pi}]]` animates a sampled 2D trajectory. `Animate[Plot[Sin[x-a],{x,-Pi,Pi}],{a,0,2 Pi}]` samples a finite parameter interval into 61 frames. General frame animation currently supports Plot and ParametricPlot. Both run from precomputed samples without repeated service calls during playback.
- `Column[{...}]` displays multiple expressions, plots or animations from one code cell, with notebook persistence. Added DSolveValue, list integration and Part/First/Last to support compact symbolic workflows.
- Explicit numerical calculations now insert all ten examples in one code cell. Equation examples include solution plots. Library groups are renamed to Analytical Solving, Numerical Solving and Postprocessing; Postprocessing includes three animation examples.
- Existing notebook v1 files remain readable; older saved notebooks are not rewritten into the new starter layout. The updated physics example can be opened from the library or its `.calix` file.
- No new external dependencies. Existing proprietary application licensing and bundled third-party notices apply.
