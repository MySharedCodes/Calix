# Calix 0.1.8

- The starter projectile uses linear drag F=-bv, m=1 kg, b=0.2 kg/s and g=9.81 m/s^2. DSolveValue computes exact velocities, Integrate computes exact displacements, and plots retain unit suffixes. The default title is unchanged; its English translation and exported filename identify linear drag.
- The planar three-body notebook replaces the trajectory animation with an animated Plot3D of potential per unit test mass. The display uses epsilon=0.15 to regularize the point-mass wells; the Newtonian dynamics and conservation diagnostics remain unchanged.
- Animate supports 61 surface frames on a 41-by-41 grid. The renderer updates the mesh, normals, color attributes and finite-triangle indices in place. Camera framing and color range remain fixed during playback; orbit controls and PNG export remain available.
- BoxRatios accepts three positive finite ratios on 3D plots. The three-body surface uses a half-height vertical ratio and a faint mesh. 3D object centering now accounts for scale, and camera fitting considers viewport aspect.
- Five-ball plots and animation cover 0 to 5 s. The relative-to-free-fall plot explicitly includes a zero curve with a legend. The animation follows the center of mass so the spring chain stays visible throughout the extended fall; plotted displacement curves still use their original reference positions.
- Gaokao Physics uses S for the area and describes all input symbols and the five symbolic outputs, followed by numerical output meanings and units.
- Notebook prose generation handles indented multiline descriptions without accidentally rendering them as code blocks.
- Workspace autosave replaces the old duplicate single-notebook backup. Old backups remain readable for migration; failed saves restore the backup and retain the previously saved workspace. Large animation outputs are no longer stored twice.
- Existing notebooks and edits are preserved. Updated examples use version 0.1.8 identities. No new dependencies.
