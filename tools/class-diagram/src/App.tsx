import { useCallback, useMemo, useEffect } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  BackgroundVariant,
  SelectionMode,
  type OnNodesChange,
  type OnSelectionChangeParams,
  type NodeMouseHandler,
  type Viewport,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { useDiagramStore } from './store';
import { useFlowNodes, useFlowEdges, getConnectedIds } from './hooks';
import { ClassNode } from './components/ClassNode';
import { GroupNode } from './components/GroupNode';
import { DetailPanel } from './components/DetailPanel';
import { Legend } from './components/Legend';
import { GroupToolbar } from './components/GroupToolbar';

const nodeTypes = {
  classNode: ClassNode,
  groupNode: GroupNode,
};

export default function App() {
  const nodes = useFlowNodes();
  const edges = useFlowEdges();

  const selectedNodeId = useDiagramStore((s) => s.selectedNodeId);
  const selectNode = useDiagramStore((s) => s.selectNode);
  const setNodePosition = useDiagramStore((s) => s.setNodePosition);
  const setViewport = useDiagramStore((s) => s.setViewport);
  const setMultiSelected = useDiagramStore((s) => s.setMultiSelected);
  const viewport = useDiagramStore((s) => s.viewport);

  // Apply selection dimming
  const styledNodes = useMemo(() => {
    if (!selectedNodeId) return nodes;
    const connected = getConnectedIds(selectedNodeId);
    return nodes.map((n) => ({
      ...n,
      className: connected.has(n.id) || n.id === selectedNodeId ? '' : 'opacity-[0.12]',
    }));
  }, [nodes, selectedNodeId]);

  const styledEdges = useMemo(() => {
    if (!selectedNodeId) return edges;
    return edges.map((e) => ({
      ...e,
      style: {
        ...e.style,
        opacity: e.source === selectedNodeId || e.target === selectedNodeId ? 1 : 0.12,
      },
    }));
  }, [edges, selectedNodeId]);

  const onNodesChange: OnNodesChange = useCallback(
    (changes) => {
      for (const change of changes) {
        if (change.type === 'position' && change.position && !change.dragging) {
          setNodePosition(change.id, change.position);
        }
      }
    },
    [setNodePosition],
  );

  const onNodeClick: NodeMouseHandler = useCallback(
    (_event, node) => {
      selectNode(selectedNodeId === node.id ? null : node.id);
    },
    [selectNode, selectedNodeId],
  );

  const onPaneClick = useCallback(() => {
    selectNode(null);
  }, [selectNode]);

  const onSelectionChange = useCallback(
    ({ nodes: selectedNodes }: OnSelectionChangeParams) => {
      setMultiSelected(selectedNodes.map((n) => n.id));
    },
    [setMultiSelected],
  );

  const onMoveEnd = useCallback(
    (_event: MouseEvent | TouchEvent | null, vp: Viewport) => {
      setViewport({ x: vp.x, y: vp.y, zoom: vp.zoom });
    },
    [setViewport],
  );

  // Escape to deselect
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        selectNode(null);
        setMultiSelected([]);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [selectNode, setMultiSelected]);

  return (
    <div className="h-screen w-screen bg-[#0e0e12] text-[#e4e4eb] font-sans">
      {/* Top bar */}
      <div className="fixed top-0 left-0 right-0 h-12 bg-[#18181f] border-b border-[#2a2a35] flex items-center px-5 z-50 gap-4">
        <h1 className="text-sm font-semibold tracking-wide">
          genfxn <span className="text-[#8888a0] font-normal">src/ class map</span>
        </h1>
        <Legend />
      </div>

      {/* Canvas */}
      <div className="pt-12 h-full">
        <ReactFlow
          nodes={styledNodes}
          edges={styledEdges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          onSelectionChange={onSelectionChange}
          onMoveEnd={onMoveEnd}
          defaultViewport={viewport ?? { x: 40, y: 20, zoom: 0.85 }}
          selectionMode={SelectionMode.Partial}
          selectionKeyCode="Shift"
          fitView={!viewport}
          proOptions={{ hideAttribution: true }}
        >
          <Background variant={BackgroundVariant.Dots} color="#2a2a35" gap={20} size={1} />
          <Controls
            showInteractive={false}
            className="!bg-[#18181f] !border-[#2a2a35] !shadow-none [&>button]:!bg-[#18181f] [&>button]:!border-[#2a2a35] [&>button]:!text-[#8888a0] [&>button:hover]:!bg-[#22222b]"
          />
        </ReactFlow>
      </div>

      {/* Detail panel */}
      <DetailPanel />

      {/* Group toolbar */}
      <GroupToolbar />
    </div>
  );
}
