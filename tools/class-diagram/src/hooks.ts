import { useMemo } from 'react';
import { MarkerType, type Node, type Edge } from '@xyflow/react';
import { NODE_DEFS } from './data/nodes';
import { EDGE_DEFS } from './data/edges';
import { useDiagramStore } from './store';
import { KIND_COLORS, EDGE_COLORS, EDGE_DASH } from './theme';
import type { NodeDef, EdgeType, NodeKind } from './types';

const KIND_FILTER_MAP: Record<string, NodeKind[]> = {
  protocol: ['protocol'],
  abstract: ['abstract'],
  op: ['op', 'op-leaf'],
  space: ['space', 'space-leaf', 'space-foundational'],
  registry: ['registry'],
  types: ['types'],
};

export function useFlowNodes(): Node[] {
  const positionOverrides = useDiagramStore((s) => s.positionOverrides);
  const groups = useDiagramStore((s) => s.groups);
  const hiddenFilters = useDiagramStore((s) => s.hiddenFilters);
  const hiddenNodeIds = useDiagramStore((s) => s.hiddenNodeIds);
  const selectedNodeId = useDiagramStore((s) => s.selectedNodeId);

  return useMemo(() => {
    const hiddenKinds = new Set<NodeKind>();
    hiddenFilters.forEach((f) => {
      const kinds = KIND_FILTER_MAP[f];
      if (kinds) kinds.forEach((k) => hiddenKinds.add(k));
    });

    const groupedIds = new Set<string>();
    groups.forEach((g) => g.memberIds.forEach((id) => groupedIds.add(id)));

    const hiddenIds = new Set(hiddenNodeIds);

    const nodes: Node[] = [];

    // Regular nodes
    for (const def of NODE_DEFS) {
      if (groupedIds.has(def.id)) continue;
      if (hiddenKinds.has(def.kind)) continue;
      if (hiddenIds.has(def.id)) continue;

      const pos = positionOverrides[def.id] ?? { x: 0, y: 0 };
      nodes.push({
        id: def.id,
        type: 'classNode',
        position: pos,
        data: {
          ...def,
          color: KIND_COLORS[def.kind],
          isRelated: selectedNodeId ? undefined : true,
        },
        style: { width: def.width },
        selected: false,
      });
    }

    // Group nodes
    for (const group of groups) {
      const memberDefs = group.memberIds
        .map((id) => NODE_DEFS.find((n) => n.id === id))
        .filter((d): d is NodeDef => d != null);

      if (hiddenKinds.has(memberDefs[0]?.kind)) continue;

      const pos = positionOverrides[group.id] ?? group.position;
      const names = memberDefs.map((d) => d.id);
      const width = Math.max(200, ...memberDefs.map((d) => d.width ?? 150));

      nodes.push({
        id: group.id,
        type: 'groupNode',
        position: pos,
        data: {
          groupId: group.id,
          memberNames: names,
          memberColors: memberDefs.map((d) => KIND_COLORS[d.kind]),
          badge: `Group (${names.length})`,
        },
        style: { width },
        selected: false,
      });
    }

    return nodes;
  }, [positionOverrides, groups, hiddenFilters, hiddenNodeIds, selectedNodeId]);
}

export function useFlowEdges(): Edge[] {
  const groups = useDiagramStore((s) => s.groups);
  const hiddenFilters = useDiagramStore((s) => s.hiddenFilters);

  return useMemo(() => {
    const hiddenKinds = new Set<NodeKind>();
    const hiddenEdgeTypes = new Set<EdgeType>();
    hiddenFilters.forEach((f) => {
      if (f.startsWith('edge-')) hiddenEdgeTypes.add(f.replace('edge-', '') as EdgeType);
      else {
        const kinds = KIND_FILTER_MAP[f];
        if (kinds) kinds.forEach((k) => hiddenKinds.add(k));
      }
    });

    // Build group membership lookup
    const memberToGroup = new Map<string, string>();
    groups.forEach((g) => g.memberIds.forEach((id) => memberToGroup.set(id, g.id)));

    const resolve = (id: string) => memberToGroup.get(id) ?? id;

    const seen = new Set<string>();
    const edges: Edge[] = [];

    for (const def of EDGE_DEFS) {
      if (hiddenEdgeTypes.has(def.type)) continue;

      // Check if source/target node kinds are hidden
      const sourceDef = NODE_DEFS.find((n) => n.id === def.source);
      const targetDef = NODE_DEFS.find((n) => n.id === def.target);
      if (sourceDef && hiddenKinds.has(sourceDef.kind)) continue;
      if (targetDef && hiddenKinds.has(targetDef.kind)) continue;

      const resolvedSource = resolve(def.source);
      const resolvedTarget = resolve(def.target);

      // Skip self-loops (both in same group)
      if (resolvedSource === resolvedTarget) continue;

      // Deduplicate
      const key = `${resolvedSource}-${resolvedTarget}-${def.type}`;
      if (seen.has(key)) continue;
      seen.add(key);

      edges.push({
        id: key,
        source: resolvedSource,
        target: resolvedTarget,
        type: 'floating',
        style: {
          stroke: EDGE_COLORS[def.type],
          strokeWidth: 1.5,
          strokeDasharray: EDGE_DASH[def.type],
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: EDGE_COLORS[def.type],
          width: 12,
          height: 12,
        },
        data: { edgeType: def.type },
      });
    }

    return edges;
  }, [groups, hiddenFilters]);
}

/** Get related node IDs and relationship types for a given node */
export function getRelatedNodes(nodeId: string): {
  inherits: string[];
  inheritedBy: string[];
  composes: string[];
  composedBy: string[];
  uses: string[];
  usedBy: string[];
  registers: string[];
  registeredBy: string[];
} {
  const result = {
    inherits: [] as string[],
    inheritedBy: [] as string[],
    composes: [] as string[],
    composedBy: [] as string[],
    uses: [] as string[],
    usedBy: [] as string[],
    registers: [] as string[],
    registeredBy: [] as string[],
  };

  for (const edge of EDGE_DEFS) {
    if (edge.source === nodeId) {
      if (edge.type === 'inherits') result.inherits.push(edge.target);
      else if (edge.type === 'composes') result.composes.push(edge.target);
      else if (edge.type === 'uses') result.uses.push(edge.target);
      else if (edge.type === 'registers') result.registers.push(edge.target);
    }
    if (edge.target === nodeId) {
      if (edge.type === 'inherits') result.inheritedBy.push(edge.source);
      else if (edge.type === 'composes') result.composedBy.push(edge.source);
      else if (edge.type === 'uses') result.usedBy.push(edge.source);
      else if (edge.type === 'registers') result.registeredBy.push(edge.source);
    }
  }

  return result;
}

/** Get all node IDs connected to a given node */
export function getConnectedIds(nodeId: string): Set<string> {
  const connected = new Set<string>([nodeId]);
  for (const edge of EDGE_DEFS) {
    if (edge.source === nodeId) connected.add(edge.target);
    if (edge.target === nodeId) connected.add(edge.source);
  }
  return connected;
}
