import { useCallback } from 'react';
import { useDiagramStore } from '../store';
import { NODE_DEFS } from '../data/nodes';

export function GroupToolbar() {
  const multiSelectedIds = useDiagramStore((s) => s.multiSelectedIds);
  const createGroup = useDiagramStore((s) => s.createGroup);
  const setMultiSelected = useDiagramStore((s) => s.setMultiSelected);
  const positionOverrides = useDiagramStore((s) => s.positionOverrides);

  const handleGroup = useCallback(() => {
    // Only group actual node IDs (not group nodes)
    const nodeIds = multiSelectedIds.filter((id) => NODE_DEFS.some((n) => n.id === id));
    if (nodeIds.length < 2) return;

    const positions: Record<string, { x: number; y: number }> = {};
    let minX = Infinity;
    let minY = Infinity;

    for (const id of nodeIds) {
      const pos = positionOverrides[id] ?? { x: 0, y: 0 };
      positions[id] = pos;
      minX = Math.min(minX, pos.x);
      minY = Math.min(minY, pos.y);
    }

    createGroup(nodeIds, positions, { x: minX - 8, y: minY - 8 });
  }, [multiSelectedIds, createGroup, positionOverrides]);

  if (multiSelectedIds.length < 2) return null;

  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 bg-[#18181f] border border-[#2a2a35] rounded-lg px-4 py-2 shadow-lg">
      <span className="text-[12px] text-[#8888a0]">{multiSelectedIds.length} selected</span>
      <button
        type="button"
        className="text-[12px] px-3 py-1 rounded bg-[#6ee7b7] text-[#0e0e12] font-semibold cursor-pointer hover:bg-[#5dd4a6] transition-colors"
        onClick={handleGroup}
      >
        Group
      </button>
      <button
        type="button"
        className="text-[12px] px-3 py-1 rounded text-[#8888a0] hover:text-[#e4e4eb] cursor-pointer transition-colors"
        onClick={() => setMultiSelected([])}
      >
        Clear
      </button>
    </div>
  );
}
