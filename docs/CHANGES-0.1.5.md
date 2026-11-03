# Calix 0.1.5

- Notebook removal defaults to keeping the disk file. Saved notebooks in the desktop app offer an unchecked option to delete their source file. A separate second confirmation shows the full path before permanent deletion. Errors keep the workspace document available.
- Each notebook has an Open file location button. Saved desktop notebooks open in Windows Explorer with their source file selected. Unsaved notebooks show a save-first message. Browser notebooks cannot access source files.
- The brand subtitle now breaks immediately after the ampersand.
- Full physics and challenge examples open in separate notebooks. Repeated clicks select the existing example document and preserve edits. Ordinary calculation snippets still append cells to the current notebook.
- Added IMO 2009 Problem 6 (grasshopper jumps), with independently worded induction proof, numeric verification and plots. Original statement: https://www.imo-official.org/assets/documents/problems/2009/2009_eng.pdf . Proof reference: https://web.evanchen.cc/exams/IMO-2009-notes.pdf . There is no universal official ranking of the hardest IMO problem.
- Existing notebooks are not automatically split or edited during upgrade. Open the examples again for separate documents; previously saved combined documents remain available.
