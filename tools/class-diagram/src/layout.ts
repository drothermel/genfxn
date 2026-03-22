import dagre from '@dagrejs/dagre';
import { NODE_DEFS } from './data/nodes';
import { EDGE_DEFS } from './data/edges';

const DEFAULT_NODE_WIDTH = 200;
const DEFAULT_NODE_HEIGHT = 80;

export type LayoutDirection = 'TB' | 'LR';

export function computeLayout(
  direction: LayoutDirection = 'TB',
): Record<string, { x: number; y: number }> {
  const g = new dagre.graphlib.Graph();
  g.setGraph({
    rankdir: direction,
    nodesep: 40,
    ranksep: 80,
    edgesep: 20,
  });
  g.setDefaultEdgeLabel(() => ({}));

  for (const node of NODE_DEFS) {
    g.setNode(node.id, {
      width: node.width ?? DEFAULT_NODE_WIDTH,
      height: DEFAULT_NODE_HEIGHT + (Math.min(node.fields.length, 3) * 20),
    });
  }

  for (const edge of EDGE_DEFS) {
    g.setEdge(edge.source, edge.target);
  }

  dagre.layout(g);

  const positions: Record<string, { x: number; y: number }> = {};
  for (const node of NODE_DEFS) {
    const pos = g.node(node.id);
    // dagre returns center positions; convert to top-left for React Flow
    positions[node.id] = {
      x: pos.x - (node.width ?? DEFAULT_NODE_WIDTH) / 2,
      y: pos.y - pos.height / 2,
    };
  }

  return positions;
}
