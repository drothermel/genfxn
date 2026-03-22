import type { NodeKind, EdgeType } from './types';

export const KIND_COLORS: Record<NodeKind, string> = {
  protocol: '#6ee7b7',
  abstract: '#a78bfa',
  op: '#60a5fa',
  'op-leaf': '#93c5fd',
  space: '#fbbf24',
  'space-leaf': '#fcd34d',
  template: '#f472b6',
  registry: '#f87171',
  types: '#c084fc',
  standalone: '#fb923c',
};

export const EDGE_COLORS: Record<EdgeType, string> = {
  inherits: '#a78bfa',
  composes: '#60a5fa',
  uses: '#555570',
  registers: '#f87171',
};

export const EDGE_DASH: Record<EdgeType, string | undefined> = {
  inherits: undefined,
  composes: undefined,
  uses: '4 3',
  registers: '6 3',
};
