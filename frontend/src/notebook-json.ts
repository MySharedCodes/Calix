export function parseNotebookJSON(content: string): unknown {
  return JSON.parse(content.startsWith('\uFEFF') ? content.slice(1) : content);
}
