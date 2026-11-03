export type Trace = { x: (number | null)[]; y: (number | null)[]; z?: (number | null)[]; name: string; color?: string; width?: number; style?: 'lines' | 'markers' | 'bars' };
export type PlotResult = {
  kind: 'plot'; plot_type: 'curve' | 'curve3d' | 'surface' | 'parametric_surface' | 'contour' | 'density' | 'volume' | 'geometry3d' | 'field3d';
  title: string; axes: string[]; traces?: Trace[]; x?: number[]; y?: number[];
  z?: (number | null)[][]; size?: number; coordinates?: (number | null)[][];
  volume?: string; density_max?: number; bounds?: number[][];
  field_kind?: 'gravity' | 'magnetic'; color_range?: number[]; masses?: number[]; softening?: number;
  times?: number[]; paths?: number[][][]; colors?: string[]; labels?: string[];
  coils?: number[]; field_lines?: number[][][]; wire_mask?: number;
  primitives?: { type: 'line' | 'arrow' | 'point' | 'triangle'; points: number[][]; color: string; colors?: string[]; label: string }[];
  scalar_legend?: { range: number[]; label: string; colors: string[] };
  options?: { range?: number[]; x_range?: number[]; equal_aspect?: boolean; legend?: boolean; box_ratios?: number[]; wireframe?: boolean }; elapsed_ms: number; engine: string;
};
export type ExpressionResult = {
  kind: 'expression'; text: string; latex: string; elapsed_ms: number; engine: string;
  unresolved?: boolean; variables?: string[];
};
export type AnimationResult = {
  kind: 'animation'; animation_type: 'trajectory' | 'frames'; plot: PlotResult;
  frames?: PlotResult[]; values: number[]; parameter: string; elapsed_ms: number; engine: string;
};
export type GroupResult = { kind: 'group'; items: Result[]; elapsed_ms: number; engine: string };
export type Execution = {thread_limit:number;threads_used:number;operations:Record<string,{calls:number;threads_used:number;path:string}>};
export type Result = (PlotResult | ExpressionResult | AnimationResult | GroupResult) & { label?: string; execution?: Execution };
export type Cell = { id: string; code: string; mode: 'source' | 'math' | 'markdown'; latex?: string; result?: Result; error?: string; stale?: boolean; executed?: number };
export type NotebookFile = { format: 'calix-notebook'; version: 1; title: string; cells: Cell[] };
