import type { Cell } from './types';

export type CellHistory = { past: Cell[][]; future: Cell[][] };
export const emptyHistory = (): CellHistory => ({ past: [], future: [] });
export const inputChanged = (a: Cell[], b: Cell[]) => a.length !== b.length || a.some((cell, i) => cell.id !== b[i].id || cell.code !== b[i].code || cell.latex !== b[i].latex || cell.mode !== b[i].mode);
export function recordStructure(before: Cell[], after: Cell[], history: CellHistory): CellHistory {
  if (before.length !== after.length || before.some((cell, i) => cell.id !== after[i].id)) {
    return { past: [...history.past, before].slice(-20), future: [] };
  }
  return inputChanged(before, after) ? { ...history, future: [] } : history;
}
export function travel(cells: Cell[], history: CellHistory, direction: 'undo' | 'redo') {
  const source = direction === 'undo' ? history.past : history.future;
  if (!source.length) return { cells, history };
  const restored = source.at(-1)!.map(cell => ({ ...cell, stale: !!cell.result }));
  return {
    cells: restored,
    history: direction === 'undo'
      ? { past: source.slice(0, -1), future: [...history.future, cells].slice(-20) }
      : { past: [...history.past, cells].slice(-20), future: source.slice(0, -1) },
  };
}
