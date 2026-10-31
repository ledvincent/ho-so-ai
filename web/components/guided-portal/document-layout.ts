import type { CSSProperties } from 'react';
import pageData from '@/public/test-fixtures/na5/pages.json';
import type { Placement, WorkflowField } from '@/components/na5-demo/model';
export function position(placement: Placement): CSSProperties {
  const page = pageData[placement.page - 1]; const [x0, y0, x1, y1] = placement.bbox;
  return { left: `${x0 / page.width * 100}%`, top: `${y0 / page.height * 100}%`, width: `${(x1 - x0) / page.width * 100}%`, height: `${(y1 - y0) / page.height * 100}%` };
}
export function parts(field: WorkflowField, value: string): { placement: Placement; text: string; size: number; overflow: boolean }[] {
  if (!value) return [];
  if (field.marks) { const placement = field.marks[value]; return placement ? [{ placement, text: '×', size: 11, overflow: false }] : []; }
  let texts = [value];
  const context = typeof document === 'undefined' ? null : document.createElement('canvas').getContext('2d');
  const width = (text: string, size: number) => { if (!context) return text.length * size * .6; context.font = `${size}px Arial`; return context.measureText(text).width; };
  if (field.type === 'date') {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return [];
    const [year, month, day] = value.split('-'); const components: Record<string, string> = { year, month, day };
    texts = field.placements.map(p => components[p.component ?? ''] ?? '');
  } else if (field.repeat) texts = field.placements.map(() => value);
  else if (field.multiline && field.placements.length) {
    const max = Math.min(...field.placements.map(p => p.bbox[2] - p.bbox[0])) - 2;
    texts = [''];
    for (const word of value.split(/\s+/)) { const next = `${texts[texts.length - 1]} ${word}`.trim(); if (width(next, 9) > max) texts.push(word); else texts[texts.length - 1] = next; }
  }
  return field.placements.flatMap((placement, index) => {
    const text = texts[index]; if (!text) return [];
    let size = 10; const max = placement.bbox[2] - placement.bbox[0] - 2;
    while (size > 7.5 && width(text, size) > max) size -= .25;
    return [{ placement, text, size, overflow: width(text, size) > max || texts.length > field.placements.length }];
  });
}
