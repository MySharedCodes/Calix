# Calix 0.1.22

- Track successful source cells per live calculation session. Missing or edited
  preceding cells are replayed for authored examples and previously evaluated
  notebooks before a dependent single-cell calculation.
- Add Wolfram `Block[{symbols}, expression]` local scopes, including restoration
  after errors, and allow storing plot results in variables.
- Put gear stress postprocessing in a local scope so it preserves the contact
  matrix, constraints and solve results. Update an existing unmodified 0.1.21
  gear example on load; preserve notebooks with edited calculation sources.
- Replace the raw `Length` exception for unresolved inputs with a dependency
  message identifying the missing variable.
- Pass the CPU Workers setting into native matrix products and element assembly;
  confine Windows calculation processes to the physical-core budget.
- Return and display actual native operation paths and thread counts. SparseLU
  and interpreted symbolic/postprocessing phases remain serial.
- Verify actual AVX2 execution on the development CPU. AVX-512 and AMX binaries
  remain available for compatible hardware, but cannot be executed on this CPU.

The reported legacy error during Run All could not be reproduced consistently
from the saved notebook source. The updated full workflow and repeated final
postprocessing are checked separately; no unique legacy root cause is asserted.
