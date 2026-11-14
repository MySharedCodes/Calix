import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import remarkRehype from 'remark-rehype';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize, { defaultSchema, type Options } from 'rehype-sanitize';
import { visit } from 'unist-util-visit';
import type { Element, Root } from 'hast';

export const fontSizes = [8, 10, 12, 14, 16, 18, 20, 24, 28, 32, 40, 48, 64, 72] as const;
export function safeFontSize(value: unknown): number | undefined {
  const size = Number(String(value ?? '').replace(/px$/, ''));
  return fontSizes.includes(size as typeof fontSizes[number]) ? size : undefined;
}

// Only a bounded text-size attribute crosses the Markdown/HTML boundary.
export const textSchema: Options = {
  ...defaultSchema,
  tagNames: [...(defaultSchema.tagNames ?? []), 'u'],
  attributes: {
    ...defaultSchema.attributes,
    span: [...(defaultSchema.attributes?.span ?? []), ['dataCixSize', ...fontSizes.map(String)]],
    code: [...(defaultSchema.attributes?.code ?? []), ['className', /^language-./, 'math-inline', 'math-display']],
  },
};
export type NotebookHeading = { id: string; cellId: string; level: number; title: string };
export const headingId = (cellId: string, ordinal: number) => `cix-heading-${cellId}-${ordinal}`;

function plainText(node: Element): string {
  return node.children.map(child => child.type === 'text' ? child.value : child.type === 'element' ? plainText(child) : '').join('');
}

export function headingsInTree(tree: Root, cellId: string): NotebookHeading[] {
  const headings: NotebookHeading[] = [];
  visit(tree, 'element', node => {
    if (!/^h[1-6]$/.test(node.tagName)) return;
    const id = headingId(cellId, headings.length);
    node.properties.id = id;
    node.properties.tabIndex = -1;
    headings.push({ id, cellId, level: Number(node.tagName[1]), title: plainText(node).trim() });
  });
  return headings;
}

const parser = unified().use(remarkParse).use(remarkGfm).use(remarkMath)
  .use(remarkRehype, { allowDangerousHtml: true }).use(rehypeRaw).use(rehypeSanitize, textSchema);
export function textHeadings(source: string, cellId: string): NotebookHeading[] {
  const tree = parser.runSync(parser.parse(source)) as Root;
  return headingsInTree(tree, cellId);
}
export function rehypeHeadingIds({ cellId }: { cellId: string }) {
  return (tree: Root) => { headingsInTree(tree, cellId); };
}
