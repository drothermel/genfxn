import { useState, useEffect, useRef } from 'react';
import { useDiagramStore } from '../store';

export function HiddenNodesDropdown() {
  const hiddenNodeIds = useDiagramStore((s) => s.hiddenNodeIds);
  const showNode = useDiagramStore((s) => s.showNode);
  const showAllNodes = useDiagramStore((s) => s.showAllNodes);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  if (hiddenNodeIds.length === 0) return null;

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        className="px-2.5 py-1 text-[11px] rounded-full bg-[#2a2a35] text-[#8888a0] hover:text-[#e4e4eb] cursor-pointer transition-colors"
        onClick={() => setOpen((o) => !o)}
      >
        Hidden ({hiddenNodeIds.length})
      </button>

      {open && (
        <div className="absolute top-8 left-0 z-[100] bg-[#18181f] border border-[#2a2a35] rounded-lg shadow-lg min-w-[180px] py-1">
          {hiddenNodeIds.map((id) => (
            <div
              key={id}
              className="flex items-center justify-between px-3 py-1.5 text-[11px] hover:bg-[#22222b]"
            >
              <span className="font-mono text-[#e4e4eb]">{id}</span>
              <button
                type="button"
                className="text-[#8888a0] hover:text-[#6ee7b7] cursor-pointer text-[10px] ml-3"
                onClick={() => showNode(id)}
              >
                show
              </button>
            </div>
          ))}
          <div className="border-t border-[#2a2a35] mt-1 pt-1 px-3 py-1.5">
            <button
              type="button"
              className="text-[11px] text-[#8888a0] hover:text-[#6ee7b7] cursor-pointer"
              onClick={() => {
                showAllNodes();
                setOpen(false);
              }}
            >
              Show all
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
